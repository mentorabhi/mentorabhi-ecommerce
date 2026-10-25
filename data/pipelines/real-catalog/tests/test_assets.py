from io import BytesIO
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assets import allowed, inspect_photo, local_path


class PhotographValidationTest(unittest.TestCase):
    def test_download_host_and_local_path_are_bounded(self):
        allowed("https://cricketershop.com/cdn/shop/files/model.jpg")
        for url in ("http://soccer90.com/a.jpg", "https://soccer90.com.evil.invalid/a.jpg",
                    "https://user:password@soccer90.com/a.jpg", "https://localhost/a.jpg"):
            with self.assertRaises(ValueError):
                allowed(url)
        for key in ("../private.jpg", "/tmp/a.jpg", "catalog-real/../secret.jpg", "catalog-real/model.svg"):
            with self.assertRaises(ValueError):
                local_path({"assetKey": key})

    def test_html_and_svg_are_not_photographs(self):
        from PIL import UnidentifiedImageError
        for content in (b"<html>Unavailable</html>", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'):
            with self.assertRaises(UnidentifiedImageError):
                inspect_photo(content)

    def test_format_is_decoded_from_bytes_and_dimensions_are_checked(self):
        from PIL import Image
        # Only a tiny in-memory validation fixture, never used as catalog artwork.
        buffer = BytesIO()
        Image.new("RGB", (200, 200), "white").save(buffer, format="JPEG")
        result = inspect_photo(buffer.getvalue())
        self.assertEqual((200, 200, "jpg"), (result["width"], result["height"], result["extension"]))
        small = BytesIO()
        Image.new("RGB", (100, 100), "white").save(small, format="PNG")
        with self.assertRaisesRegex(ValueError, "bounded"):
            inspect_photo(small.getvalue())


if __name__ == "__main__":
    unittest.main()
