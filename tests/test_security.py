import io
import unittest

from PIL import Image

from src.security import validate_uploaded_image


class FakeUpload(io.BytesIO):
    @property
    def size(self):
        return len(self.getvalue())


def make_image_bytes(fmt="PNG", size=(120, 80)):
    image = Image.new("RGB", size, "white")
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


class SecurityTests(unittest.TestCase):
    def test_valid_png_is_accepted(self):
        upload = FakeUpload(make_image_bytes("PNG"))
        image, error = validate_uploaded_image(upload)
        self.assertIsNone(error)
        self.assertIsNotNone(image)
        self.assertEqual(image.mode, "RGB")

    def test_valid_jpeg_is_accepted(self):
        upload = FakeUpload(make_image_bytes("JPEG"))
        image, error = validate_uploaded_image(upload)
        self.assertIsNone(error)
        self.assertIsNotNone(image)

    def test_fake_png_is_rejected(self):
        upload = FakeUpload(b"this is not actually a PNG")
        image, error = validate_uploaded_image(upload)
        self.assertIsNone(image)
        self.assertIsNotNone(error)

    def test_oversized_file_is_rejected_before_decode(self):
        upload = FakeUpload(b"x" * (10 * 1024 * 1024 + 1))
        image, error = validate_uploaded_image(upload)
        self.assertIsNone(image)
        self.assertIn("10 MB", error)


if __name__ == "__main__":
    unittest.main()
