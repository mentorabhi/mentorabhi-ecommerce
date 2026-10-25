"""Restore original manufacturer PDF image pixels, including source soft masks."""
import hashlib
from io import BytesIO
from functools import lru_cache
from pathlib import Path
import re
from urllib.request import Request, urlopen

from assets import ROOT, inspect_photo

DSC_URL = "https://dsc-cricket.co.uk/media/ecatalog/UK-CATALOG-2022.pdf"
DSC_SHA256 = "6f70a08f07b2ad46158817cb83d7774db3ff204139bf60b2bb6515d308e6afcc"
MAX_PDF_BYTES = 48 * 1024 * 1024


def validate_locator(locator):
    if locator.get("url") != DSC_URL or locator.get("sha256") != DSC_SHA256:
        raise ValueError("PDF must be the reviewed manufacturer source/hash")
    if type(locator.get("page")) is not int or not 1 <= locator["page"] <= 78:
        raise ValueError("Invalid manufacturer PDF page")
    if not re.fullmatch(r"/Im[0-9]+", locator.get("object", "")):
        raise ValueError("Invalid embedded photograph locator")


@lru_cache(maxsize=1)
def document():
    from pypdf import PdfReader
    path = ROOT / "devops/.local/catalog-research/dsc-uk-catalog-2022.pdf"
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing symlinked manufacturer source")
    if not path.exists():
        with urlopen(Request(DSC_URL, headers={"User-Agent": "SuperSports-Learning-Catalog/1.0"}), timeout=45) as response:
            data = response.read(MAX_PDF_BYTES + 1)
        if len(data) > MAX_PDF_BYTES or hashlib.sha256(data).hexdigest() != DSC_SHA256:
            raise ValueError("Manufacturer source changed; review before accepting a new PDF")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if path.stat().st_size > MAX_PDF_BYTES or hashlib.sha256(path.read_bytes()).hexdigest() != DSC_SHA256:
        raise ValueError("Local manufacturer PDF differs from the reviewed hash")
    return PdfReader(path)


def extract_photo(locator):
    validate_locator(locator)
    page = document().pages[locator["page"] - 1]
    # pypdf reconstructs the original image + alpha mask; no generated or retouched pixels.
    image = page.images[locator["object"]]
    # Masked source JPEGs may be returned as JP2. Encode the decoded original RGBA
    # pixels losslessly as browser-compatible PNG, retaining the source alpha.
    buffer = BytesIO()
    image.image.save(buffer, format="PNG")
    data = buffer.getvalue()
    return data, inspect_photo(data)
