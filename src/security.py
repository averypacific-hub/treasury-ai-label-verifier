import hashlib
import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_DIMENSION = 6000
MAX_PIXELS = 20_000_000
AI_MAX_DIMENSION = 1800
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}


def validate_uploaded_image(uploaded_file):
    """Validate and sanitize an uploaded label image before AI processing.

    Security controls:
    - 10 MB maximum file size
    - actual image decoding instead of trusting the filename extension
    - JPEG/PNG only
    - dimension and total-pixel limits
    - EXIF orientation applied
    - metadata removed from the in-memory image object
    - image downscaled before API submission to control latency and cost
    - no intentional disk persistence
    """
    if uploaded_file is None:
        return None, "No file uploaded."

    if uploaded_file.size > MAX_FILE_SIZE:
        return None, "File is too large. Maximum allowed size is 10 MB."

    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            uploaded_file.seek(0)
            probe = Image.open(uploaded_file)
            detected_format = probe.format
            probe.verify()

            if detected_format not in ALLOWED_IMAGE_FORMATS:
                return None, "Unsupported image format. Use JPG, JPEG, or PNG."

            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            image = ImageOps.exif_transpose(image)
            image.load()

        width, height = image.size
        pixels = width * height

        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            return None, (
                f"Image dimensions exceed {MAX_DIMENSION} pixels on one side."
            )

        if pixels > MAX_PIXELS:
            return None, "Image contains too many pixels for safe processing."

        if image.mode != "RGB":
            image = image.convert("RGB")

        # Make a clean in-memory pixel copy. Saving later without EXIF/ICC arguments
        # prevents original metadata from being transmitted to the AI service.
        clean = image.copy()
        clean.info.clear()
        clean.thumbnail(
            (AI_MAX_DIMENSION, AI_MAX_DIMENSION),
            Image.Resampling.LANCZOS,
        )

        uploaded_file.seek(0)
        return clean, None

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        return None, "The uploaded file is not a valid supported image."
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit


def image_fingerprint(image):
    """Return a SHA-256 fingerprint of the sanitized image."""
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return hashlib.sha256(buffer.getvalue()).hexdigest()
