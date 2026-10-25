"""Download/verify source photographs, or restore the exact accepted local bundle."""
from __future__ import annotations
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "apps/storefront/public/catalog-real"
HOSTS = frozenset(("cricketershop.com", "soccer90.com", "cdn.shopify.com"))
MAX_BYTES = 12 * 1024 * 1024


def allowed(url):
    value = urlsplit(url)
    if value.scheme != "https" or value.hostname not in HOSTS or value.username or value.password or value.port not in (None, 443):
        raise ValueError("Photograph URL is outside the accepted public source hosts")


class SourceRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        allowed(url)
        return super().redirect_request(request, fp, code, message, headers, url)


def inspect_photo(data):
    from PIL import Image
    import warnings
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Photograph size is invalid")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}.get(image.format)
            if not extension or min(width, height) < 180 or max(width, height) > 6000 or width * height > 16_000_000:
                raise ValueError("Expected a bounded, usable JPEG/PNG/WebP photograph")
            image.verify()
    return {"sha256": hashlib.sha256(data).hexdigest(), "width": width, "height": height, "extension": extension, "kind": "photograph"}


def download(url):
    allowed(url)
    request = Request(url, headers={"Accept": "image/jpeg,image/png,image/webp", "User-Agent": "SuperSports-Learning-Catalog/1.0"})
    with build_opener(SourceRedirects()).open(request, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    return data, inspect_photo(data)


def store(data, key, metadata):
    if not re.fullmatch(r"[a-f0-9]{64}", key):
        raise ValueError("Invalid source key")
    ASSETS.mkdir(parents=True, exist_ok=True)
    if ASSETS.is_symlink():
        raise ValueError("Refusing a symlinked photo directory")
    filename = f"{key}.{metadata['extension']}"
    with tempfile.NamedTemporaryFile(dir=ASSETS, delete=False) as handle:
        handle.write(data); temporary = Path(handle.name)
    temporary.chmod(0o644)
    temporary.replace(ASSETS / filename)
    return {**metadata, "assetKey": "catalog-real/" + filename}


def local_path(image):
    key = image["assetKey"]
    if not re.fullmatch(r"catalog-real/[a-f0-9]{64}\.(jpg|png|webp)", key):
        raise ValueError("Invalid local photo key")
    path = ROOT / "apps/storefront/public" / key
    if path.is_symlink():
        raise ValueError("Refusing symlinked local photograph")
    return path


def verify_local(image):
    observed = inspect_photo(local_path(image).read_bytes())
    if any(observed[field] != image[field] for field in ("sha256", "width", "height", "extension", "kind")):
        raise ValueError("Local photograph differs from accepted source manifest")


def restore(manifest):
    for product in manifest["products"]:
        image = product["image"]
        path = local_path(image)
        if not path.exists():
            if image.get("pdfImage"):
                from pdf_assets import extract_photo
                data, metadata = extract_photo(image["pdfImage"])
            else:
                data, metadata = download(image["url"])
            if metadata["sha256"] != image["sha256"]:
                raise ValueError("Source photograph changed; re-review it before updating the manifest")
            store(data, product["sourceKey"], metadata)
        verify_local(image)
        path.chmod(0o644)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    restore(json.loads(parser.parse_args().manifest.read_text()))
    print("Accepted local photograph bundle restored and verified")
