# AI-Powered Alcohol Label Verification

A standalone prototype that compares visible alcohol-label information against application data and produces explainable reviewer results.

## Why this implementation is different

The prototype does not simply ask a model whether a label "looks right." It separates AI extraction from deterministic verification:

1. Validate and sanitize the uploaded image.
2. Extract structured fields with a vision-capable model.
3. Validate the model output with Pydantic.
4. Apply deterministic comparison rules for text, ABV, volume, import country, and the government warning.
5. Display side-by-side evidence and route uncertainty to human review.
6. Allow the reviewer to download a JSON verification record.

## Implemented requirements

- Brand name comparison
- Class/type comparison
- Alcohol-content comparison
- Net-contents comparison, including equivalent mL/L/cL forms
- Producer/bottler comparison
- Country of origin when the product is identified as imported
- Strict government-warning text and visible-format checks
- Processing-time measurement against the approximately 5-second stakeholder target
- Simple single-page reviewer workflow
- Graceful failure and human-review states
- Standalone proof of concept with no COLA integration

## Government warning

The application checks the warning for:

- presence
- exact required wording, capitalization, and punctuation, allowing only whitespace normalization
- `GOVERNMENT WARNING` in all capitals
- `GOVERNMENT WARNING` appearing bold
- the remainder not appearing bold
- continuous paragraph presentation
- separation from surrounding information
- visual readability in the submitted image

### Deliberate limitation: physical type size

Physical type-size requirements cannot be reliably measured from an arbitrary photograph without a scale reference. The prototype therefore does not claim that determination and leaves it to human or scale-aware review.

## Security posture

See [`SECURITY.md`](SECURITY.md). Key controls include secure secret handling, 10 MB upload limits, real image decoding, decompression-bomb protection, metadata removal, in-memory processing, structured-output validation, `store=False`, prompt-injection resistance, safe errors, and API-call safeguards.

## Setup

### Prerequisites

- Python 3.12+
- Git
- VS Code or another editor

### Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and place the API key there:

```text
OPENAI_API_KEY=...
```

Never commit `.env`.

### Run tests

```powershell
python -m unittest discover -s tests -v
```

### Run the app

```powershell
python -m streamlit run app.py
```

## Test data

`sample_data/TEST.png` is synthetic test data included only for demonstration and development.

## Assumptions and trade-offs

- Use synthetic/public data only for this take-home prototype.
- AI output supports reviewer judgment and is not an authorized final determination.
- Country of origin is evaluated only when the application identifies the product as imported.
- Poor-angle, glare, and low-resolution handling should be evaluated with a dedicated test set before production use.
- Batch processing is a useful stakeholder-requested enhancement, but this submission prioritizes a complete and reliable core workflow over a partially implemented batch feature.
- Production deployment would require agency-approved hosting, identity/access controls, monitoring, retention decisions, and formal authorization.

## Repository layout

```text
app.py
src/
  __init__.py
  ai_extractor.py
  security.py
  validators.py
tests/
  __init__.py
  test_security.py
  test_validators.py
sample_data/
  TEST.png
.streamlit/
  config.toml
.env.example
.gitignore
requirements.txt
README.md
SECURITY.md
```
