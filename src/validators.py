import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

CANONICAL_GOVERNMENT_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
}


def normalize_generic_text(value):
    """Conservative normalization for ordinary label/application text."""
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_whitespace_only(value):
    """Collapse whitespace while preserving case and punctuation."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip())


def compare_text_values(application_value, extracted_value):
    if not application_value or not extracted_value:
        return "NEEDS REVIEW"
    return (
        "MATCH"
        if normalize_generic_text(application_value)
        == normalize_generic_text(extracted_value)
        else "MISMATCH"
    )


def extract_number(value):
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group()) if match else None


def compare_alcohol_content(application_value, extracted_value):
    if not application_value or not extracted_value:
        return "NEEDS REVIEW"
    app = extract_number(application_value)
    label = extract_number(extracted_value)
    if app is None or label is None:
        return "NEEDS REVIEW"
    return "MATCH" if abs(app - label) < 0.001 else "MISMATCH"


def normalize_net_contents(value):
    """Normalize common mL/L/cL forms to milliliters."""
    if not value:
        return None

    cleaned = value.lower().strip()
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(ml|milliliters?|millilitres?|cl|centiliters?|centilitres?|"
        r"l|liters?|litres?)\b",
        cleaned,
    )
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2)

    if unit.startswith("ml") or unit.startswith("milli"):
        return number
    if unit.startswith("cl") or unit.startswith("centi"):
        return number * 10
    return number * 1000


def compare_net_contents(application_value, extracted_value):
    if not application_value or not extracted_value:
        return "NEEDS REVIEW"
    app = normalize_net_contents(application_value)
    label = normalize_net_contents(extracted_value)
    if app is None or label is None:
        return "NEEDS REVIEW"
    return "MATCH" if abs(app - label) < 0.01 else "MISMATCH"



def normalize_producer(value):
    """
    Normalize producer/bottler statements while preserving organization identity.

    Examples treated as the same producer:
    - Sunridge Vineyards
    - Bottled by Sunridge Vineyards
    - Bottled by Sunridge Vineyards, Napa, California
    """
    if not value:
        return ""

    cleaned = value.lower().strip()

    prefixes = (
        "produced and bottled by",
        "cellared and bottled by",
        "vinted and bottled by",
        "produced by",
        "bottled by",
        "imported by",
        "distributed by",
    )

    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def compare_producer(application_value, extracted_value):
    """
    Compare producer/bottler identity while allowing normal label prefixes
    and trailing address/location text.
    """
    if not application_value or not extracted_value:
        return "NEEDS REVIEW"

    application = normalize_producer(application_value)
    extracted = normalize_producer(extracted_value)

    if not application or not extracted:
        return "NEEDS REVIEW"

    if application == extracted:
        return "MATCH"

    # Allow a producer name followed by location/address information.
    if extracted.startswith(application + " "):
        return "MATCH"

    if application.startswith(extracted + " "):
        return "MATCH"

    return "MISMATCH"

def normalize_country(value):
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.lower() in US_STATES:
        return None
    return cleaned


class LabelExtraction(BaseModel):
    brand_name: Optional[str] = Field(default=None)
    product_type: Optional[str] = Field(default=None)
    alcohol_content: Optional[str] = Field(default=None)
    net_contents: Optional[str] = Field(default=None)
    producer_name: Optional[str] = Field(default=None)
    country_of_origin: Optional[str] = Field(default=None)

    government_warning: Optional[str] = Field(default=None)
    government_warning_present: Optional[bool] = Field(default=None)
    warning_header_all_caps: Optional[bool] = Field(default=None)
    warning_header_bold: Optional[bool] = Field(default=None)
    warning_body_not_bold: Optional[bool] = Field(default=None)
    warning_continuous_paragraph: Optional[bool] = Field(default=None)
    warning_separate_from_other_info: Optional[bool] = Field(default=None)
    warning_readable: Optional[bool] = Field(default=None)

    extraction_notes: Optional[str] = Field(default=None)

    @field_validator(
        "brand_name",
        "product_type",
        "alcohol_content",
        "net_contents",
        "producer_name",
        "government_warning",
        "extraction_notes",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if not value:
            return None
        if len(value) > 5000:
            raise ValueError("Extracted field exceeds allowed length.")
        return value

    @field_validator("country_of_origin", mode="before")
    @classmethod
    def validate_country(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if not value:
            return None
        if len(value) > 200:
            raise ValueError("Country field exceeds allowed length.")
        return normalize_country(value)


def evaluate_government_warning(extraction: LabelExtraction):
    """Strictly evaluate warning wording plus visible formatting evidence."""
    exact_text = None
    if extraction.government_warning:
        exact_text = (
            normalize_whitespace_only(extraction.government_warning)
            == normalize_whitespace_only(CANONICAL_GOVERNMENT_WARNING)
        )

    checks = {
        "present": extraction.government_warning_present,
        "exact_text": exact_text,
        "header_all_caps": extraction.warning_header_all_caps,
        "header_bold": extraction.warning_header_bold,
        "body_not_bold": extraction.warning_body_not_bold,
        "continuous_paragraph": extraction.warning_continuous_paragraph,
        "separate_from_other_info": extraction.warning_separate_from_other_info,
        "readable": extraction.warning_readable,
    }

    if any(value is False for value in checks.values()):
        status = "MISMATCH"
    elif any(value is None for value in checks.values()):
        status = "NEEDS REVIEW"
    else:
        status = "MATCH"

    return {"status": status, "checks": checks}
