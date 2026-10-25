from io import BytesIO
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assets import allowed, inspect_photo, local_path


class PhotographValidationTest(unittest.TestCase):
    def test_public_photo_is_readable_by_the_non_owner_web_server(self):
        import assets
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(assets, "ASSETS", Path(directory)):
                assets.store(b"fixture-bytes", "a" * 64, {"extension": "jpg"})
            path = Path(directory) / ("a" * 64 + ".jpg")
            self.assertEqual(0o644, path.stat().st_mode & 0o777)
            self.assertEqual(b"fixture-bytes", path.read_bytes())

    def test_pdf_locator_rejects_unreviewed_documents_and_non_image_objects(self):
        from pdf_assets import DSC_URL, DSC_SHA256, validate_locator
        valid = {"url": DSC_URL, "sha256": DSC_SHA256, "page": 19, "object": "/Im1396"}
        validate_locator(valid)
        for changes in ({"url": "https://unreviewed.invalid/catalog.pdf"}, {"sha256": "0" * 64},
                        {"page": 0}, {"page": 79}, {"object": "../../private"}):
            with self.assertRaises(ValueError):
                validate_locator({**valid, **changes})

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
