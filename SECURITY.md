# Security Notes

This repository is a take-home prototype, not a production authorization boundary.

## Controls implemented

- API key loaded from environment/deployment secret storage; never committed.
- OpenAI Responses calls use `store=False`.
- Uploaded files are capped at 10 MB and restricted to JPEG/PNG.
- Actual image decoding is required; filename extensions are not trusted.
- Decompression-bomb warnings are treated as errors during validation.
- Dimension and total-pixel limits are applied before AI processing.
- EXIF orientation is handled; original metadata is not transmitted.
- Images are downscaled before AI submission to reduce cost and latency.
- Uploaded images are processed in memory and not intentionally persisted.
- Image text is treated as untrusted data and not as model instructions.
- AI output must pass a Pydantic schema before application logic uses it.
- Raw API exceptions are not exposed in the user interface.
- Duplicate-image reuse and a per-session call safeguard reduce accidental API spend.
- Reviewer-facing output clearly distinguishes MATCH, MISMATCH, NEEDS REVIEW, and N/A.

## Data handling boundary

Use only synthetic or public test data in this prototype. Do not upload CUI, PII, classified information, credentials, or sensitive government data.

This repository does not claim Treasury production approval, an ATO, CUI authorization, Zero Data Retention, or any other agency authorization.
