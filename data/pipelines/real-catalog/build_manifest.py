"""Build the attributed catalog from a manually curated source list (data phase)."""
import argparse
from datetime import date
import json
from pathlib import Path

from assets import download, store
from catalog_data import prepare_model, source_key, validate_manifest


def build(candidates):
    products = []
    for source in candidates:
        # Sources must be curated before acquisition; failures stop this batch.
        data, metadata = download(source["imageUrl"])
        image = store(data, source_key(source["sourceUrl"]), metadata)
        products.append(prepare_model(source, image))
    manifest = {"version": 1, "capturedOn": date.today().isoformat(),
                "fixtureInrPerUsd": "85.00", "products": products}
    validate_manifest(manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build(json.loads(args.candidates.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps(validate_manifest(result)))


if __name__ == "__main__":
    main()
