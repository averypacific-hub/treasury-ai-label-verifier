import json
import os
import time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from src.ai_extractor import AIExtractionError, extract_label_information
from src.security import image_fingerprint, validate_uploaded_image
from src.validators import (
    CANONICAL_GOVERNMENT_WARNING,
    compare_alcohol_content,
    compare_net_contents,
    compare_producer,
    compare_text_values,
    evaluate_government_warning,
)

load_dotenv()

MAX_AI_CALLS_PER_SESSION = 10

st.set_page_config(
    page_title="AI-Powered Alcohol Label Verification",
    page_icon="🔎",
    layout="wide",
)

st.title("AI-Powered Alcohol Label Verification")
st.write(
    "AI-assisted comparison of alcohol-label information against submitted "
    "application data, with explainable verification evidence."
)
st.caption(
    "Prototype only. Use synthetic or public test data. Do not submit CUI, PII, "
    "classified information, credentials, or sensitive government data."
)

if "ai_call_count" not in st.session_state:
    st.session_state.ai_call_count = 0

st.divider()
st.subheader("1. Application Data")

left, right = st.columns(2)
with left:
    brand_name = st.text_input("Brand Name")
    product_type = st.text_input("Product Type / Class")
    alcohol_content = st.text_input("Alcohol Content (ABV)")
with right:
    net_contents = st.text_input("Net Contents")
    producer_name = st.text_input("Producer / Bottler Name")
    imported_product = st.checkbox("Imported product")
    country_origin = st.text_input(
        "Country of Origin",
        disabled=not imported_product,
        help="Required for imports. Leave unchecked for domestic products.",
    )

with st.expander("Government warning reference"):
    st.code(CANONICAL_GOVERNMENT_WARNING, language=None)
    st.caption(
        "The required text and visible formatting are checked separately. "
        "Absolute physical type size cannot be reliably measured from an arbitrary photo."
    )

st.divider()
st.subheader("2. Upload Label")
st.caption(
    "JPG/JPEG/PNG only; maximum 10 MB; actual image decoding; metadata stripped; "
    "image dimensions and pixel count constrained before AI processing."
)

uploaded_file = st.file_uploader(
    "Upload alcohol label image",
    type=["jpg", "jpeg", "png"],
    max_upload_size=10,
)

validated_image = None
current_hash = None

if uploaded_file is not None:
    validated_image, upload_error = validate_uploaded_image(uploaded_file)
    if upload_error:
        st.error(upload_error)
    else:
        st.success("Image passed security validation.")
        st.image(validated_image, caption="Validated label image", width=500)
        current_hash = image_fingerprint(validated_image)

st.divider()
st.subheader("3. AI Label Analysis")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error(
        "AI service is not configured. Set OPENAI_API_KEY in your local .env file "
        "or deployment secret store."
    )

if validated_image is not None and api_key:
    remaining = MAX_AI_CALLS_PER_SESSION - st.session_state.ai_call_count
    st.caption(f"Session AI-call safeguard: {remaining} call(s) remaining.")

    action_col, clear_col = st.columns([3, 1])
    with action_col:
        analyze_clicked = st.button("Analyze Label with AI", type="primary")
    with clear_col:
        clear_clicked = st.button("Clear analysis")

    if clear_clicked:
        for key in ("ai_result", "analyzed_image_hash", "analysis_time"):
            st.session_state.pop(key, None)
        st.rerun()

    if analyze_clicked:
        previous_hash = st.session_state.get("analyzed_image_hash")
        previous_result = st.session_state.get("ai_result")

        if previous_hash == current_hash and previous_result is not None:
            st.info(
                "This exact image was already analyzed in this session. "
                "Reusing the prior result to avoid an unnecessary API charge."
            )
        elif st.session_state.ai_call_count >= MAX_AI_CALLS_PER_SESSION:
            st.error(
                "Session AI-call limit reached. Start a new session if additional "
                "authorized testing is required."
            )
        else:
            try:
                client = OpenAI(api_key=api_key)
                start = time.perf_counter()
                with st.spinner("Analyzing label..."):
                    result = extract_label_information(
                        image=validated_image,
                        client=client,
                    )
                elapsed = time.perf_counter() - start

                st.session_state.ai_call_count += 1
                st.session_state.ai_result = result
                st.session_state.analyzed_image_hash = current_hash
                st.session_state.analysis_time = elapsed

            except AIExtractionError:
                st.error(
                    "AI label analysis could not be completed. "
                    "No verification determination was made."
                )

result = st.session_state.get("ai_result")
result_hash = st.session_state.get("analyzed_image_hash")


def display_value(value):
    return value if value not in (None, "") else "Not reliably identified"


if result is not None and result_hash == current_hash:
    st.success("AI extraction completed and passed structured-output validation.")

    elapsed = st.session_state.get("analysis_time")
    if elapsed is not None:
        if elapsed <= 5:
            st.caption(f"Processing time: {elapsed:.2f} seconds (target met)")
        else:
            st.warning(
                f"Processing time: {elapsed:.2f} seconds. "
                "Stakeholder target is approximately 5 seconds."
            )

    st.markdown("#### Extracted Label Information")
    e1, e2 = st.columns(2)
    with e1:
        st.text_input("Extracted Brand Name", value=display_value(result.brand_name), disabled=True)
        st.text_input("Extracted Product Type / Class", value=display_value(result.product_type), disabled=True)
        st.text_input("Extracted Alcohol Content", value=display_value(result.alcohol_content), disabled=True)
    with e2:
        st.text_input("Extracted Net Contents", value=display_value(result.net_contents), disabled=True)
        st.text_input("Extracted Producer / Bottler", value=display_value(result.producer_name), disabled=True)
        st.text_input("Extracted Country of Origin", value=display_value(result.country_of_origin), disabled=True)

    if result.extraction_notes:
        with st.expander("AI Extraction Notes"):
            st.write(result.extraction_notes)

    st.divider()
    st.subheader("4. Verification Results")

    country_status = (
        compare_text_values(country_origin, result.country_of_origin)
        if imported_product
        else "NOT APPLICABLE"
    )
    warning_eval = evaluate_government_warning(result)

    verification_results = {
        "Brand Name": compare_text_values(brand_name, result.brand_name),
        "Product Type / Class": compare_text_values(product_type, result.product_type),
        "Alcohol Content": compare_alcohol_content(alcohol_content, result.alcohol_content),
        "Net Contents": compare_net_contents(net_contents, result.net_contents),
        "Producer / Bottler": compare_producer(producer_name, result.producer_name),
        "Country of Origin": country_status,
        "Government Warning": warning_eval["status"],
    }

    evidence = {
        "Brand Name": (brand_name, result.brand_name),
        "Product Type / Class": (product_type, result.product_type),
        "Alcohol Content": (alcohol_content, result.alcohol_content),
        "Net Contents": (net_contents, result.net_contents),
        "Producer / Bottler": (producer_name, result.producer_name),
        "Country of Origin": (
            country_origin if imported_product else "Not required for domestic product",
            result.country_of_origin,
        ),
        "Government Warning": (
            "Exact required text + required visible formatting",
            result.government_warning,
        ),
    }

    match_count = mismatch_count = review_count = na_count = 0

    for field, status in verification_results.items():
        app_value, label_value = evidence[field]
        with st.container(border=True):
            st.markdown(f"**{field}**")
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.caption("Application / Requirement")
                st.write(display_value(app_value))
            with c2:
                st.caption("Label / Evidence")
                st.write(display_value(label_value))
            with c3:
                st.caption("Result")
                if status == "MATCH":
                    st.success("MATCH")
                    match_count += 1
                elif status == "MISMATCH":
                    st.error("MISMATCH")
                    mismatch_count += 1
                elif status == "NOT APPLICABLE":
                    st.info("N/A")
                    na_count += 1
                else:
                    st.warning("NEEDS REVIEW")
                    review_count += 1

        if field == "Government Warning":
            with st.expander("Government warning validation details"):
                labels = {
                    "present": "Warning present",
                    "exact_text": "Exact required wording, capitalization, and punctuation",
                    "header_all_caps": '"GOVERNMENT WARNING" in all capitals',
                    "header_bold": '"GOVERNMENT WARNING" appears bold',
                    "body_not_bold": "Remainder does not appear bold",
                    "continuous_paragraph": "Continuous paragraph",
                    "separate_from_other_info": "Separate and apart from other information",
                    "readable": "Readily legible / visually readable",
                }
                for key, label in labels.items():
                    value = warning_eval["checks"][key]
                    if value is True:
                        st.success(f"{label}: PASS")
                    elif value is False:
                        st.error(f"{label}: FAIL")
                    else:
                        st.warning(f"{label}: NEEDS REVIEW")

                st.caption(
                    "Physical type-size compliance cannot be reliably measured from an arbitrary "
                    "image without a scale reference; the prototype therefore does not claim that determination."
                )

    st.divider()
    st.subheader("5. Review Summary")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Matches", match_count)
    m2.metric("Mismatches", mismatch_count)
    m3.metric("Needs Review", review_count)
    m4.metric("Not Applicable", na_count)

    if mismatch_count > 0:
        overall_result = "REVIEW REQUIRED"
        st.error(
            f"Overall Result: {overall_result}. "
            f"{mismatch_count} discrepancy/discrepancies detected."
        )
    elif review_count > 0:
        overall_result = "HUMAN REVIEW REQUIRED"
        st.warning(
            f"Overall Result: {overall_result}. "
            f"{review_count} field(s) could not be conclusively verified."
        )
    else:
        overall_result = "PASS"
        st.success("Overall Result: PASS")

    st.caption(
        "AI-assisted extraction supports reviewer judgment; it does not replace "
        "an authorized compliance determination."
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "prototype": "AI-Powered Alcohol Label Verification",
        "processing_seconds": round(elapsed, 3) if elapsed is not None else None,
        "overall_result": overall_result,
        "summary": {
            "matches": match_count,
            "mismatches": mismatch_count,
            "needs_review": review_count,
            "not_applicable": na_count,
        },
        "application_data": {
            "brand_name": brand_name or None,
            "product_type": product_type or None,
            "alcohol_content": alcohol_content or None,
            "net_contents": net_contents or None,
            "producer_name": producer_name or None,
            "imported_product": imported_product,
            "country_of_origin": country_origin or None,
        },
        "extracted_label_data": result.model_dump(),
        "verification_results": verification_results,
        "government_warning_checks": warning_eval["checks"],
        "limitations": [
            "Physical warning type size is not determined from arbitrary images without a scale reference.",
            "AI output supports human review and is not an authorized final determination.",
        ],
    }

    st.download_button(
        "Download verification report (JSON)",
        data=json.dumps(report, indent=2),
        file_name="label_verification_report.json",
        mime="application/json",
    )
