"""Deterministic source-model, variant and fixture-price preparation."""
from __future__ import annotations
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import re
import unicodedata
from datetime import date
from urllib.parse import urlsplit

DEMO_INR_PER_USD = Decimal("85.00")
MINIMUMS = {"cricket": (100, 1000), "football": (100, 1000)}


def source_key(url, record_id=None):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Model source must be an attributed HTTPS URL without credentials")
    path = parsed.path.split("/products/")[-1] if "/products/" in parsed.path else parsed.path
    identity = parsed.hostname.lower() + "/products/" + path.rstrip("/")
    if record_id is not None:
        if not parsed.path.lower().endswith(".pdf") or not re.fullmatch(r"[a-z0-9][a-z0-9:-]{2,160}", record_id):
            raise ValueError("PDF records need a bounded explicit manufacturer/model identity")
        identity += "|record:" + record_id
    return hashlib.sha256(identity.encode()).hexdigest()


def equipment(title, fallback):
    lower = title.lower()
    for word, kind in (("helmet", "helmet"), ("glove", "gloves"), ("pad", "pads"), ("leg guard", "pads"),
                       ("kit bag", "bag"), ("kitbag", "bag"), ("duffle", "bag"), ("backpack", "bag"), ("gym sack", "bag"), ("gymsack", "bag"),
                       ("jacket", "jacket"), ("hood", "hoodie"),
                       ("jersey", "jersey"), ("shirt", "shirt"), ("tee", "shirt"), ("sleeve", "sleeves"),
                       ("sock", "socks"), ("cleat", "boots"), ("shoe", "boots"), ("ball", "ball"), ("bat", "bat")):
        if word in lower:
            return kind
    return fallback


def money(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def variants(key, sport, kind, base_minor, source_currency, fixture_options=None):
    if type(base_minor) is not int or base_minor <= 0 or source_currency not in ("INR", "USD"):
        raise ValueError("Source fixture prices require positive integer minor units and INR/USD")
    inr = Decimal(base_minor) if source_currency == "INR" else Decimal(base_minor) * DEMO_INR_PER_USD
    if fixture_options is not None:
        if not isinstance(fixture_options,list) or not 1 <= len(fixture_options) <= 20:
            raise ValueError("Explicit fixture options must contain 1 to 20 configurations")
        options=[]
        seen=set()
        for option in fixture_options:
            attributes=option.get("attributes") if isinstance(option,dict) else None
            pack=option.get("pack",1) if isinstance(option,dict) else None
            if not isinstance(attributes,dict) or not 1 <= len(attributes) <= 8 or type(pack) is not int or not 1 <= pack <= 100:
                raise ValueError("Fixture configuration needs bounded attributes and positive pack quantity")
            if any(not isinstance(k,str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,39}",k)
                   or not isinstance(v,str) or not 1 <= len(v) <= 100 or any(ord(c)<32 or c in "<>" for c in v) for k,v in attributes.items()):
                raise ValueError("Fixture configuration attributes must be bounded plain text")
            identity=tuple(sorted(attributes.items()))
            if identity in seen:raise ValueError("Duplicate fixture configuration")
            seen.add(identity);options.append((dict(attributes),pack))
    elif kind == "ball":
        options = [(dict(pack=str(pack), size=size), pack) for pack in (1, 3, 6, 12, 24) for size in ("Adult", "Youth")]
    elif kind == "gloves" and sport == "football":
        options = [(dict(size=str(size), colour="Source colourway", pack="Pair"), 1) for size in range(4, 14)]
    elif kind in ("gloves", "pads"):
        options = [(dict(size=size, hand=hand), 1) for size in ("Junior", "Youth", "Small adult", "Adult", "Large adult") for hand in ("Right", "Left")]
    elif kind == "bat":
        options = [(dict(size=size, grip=grip), 1) for size in ("4", "5", "6", "Harrow", "Short handle") for grip in ("Source finish", "Black")]
    elif kind == "boots":
        options = [(dict(size=f"UK {size}", colour="Source colourway"), 1) for size in range(4, 14)]
    elif kind == "bag":
        options = [(dict(pack=str(pack), colour=colour), pack) for pack in (1, 2, 3, 4, 5) for colour in ("Source colourway", "Navy")]
    elif kind == "helmet":
        options = [(dict(size=size, colour=colour), 1) for size in ("XS", "S", "M", "L", "XL") for colour in ("Source colourway", "Navy")]
    else:
        options = [(dict(size=size, colour="Source colourway"), 1) for size in ("XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL")]
    result = []
    for index, (attributes, pack) in enumerate(options, 1):
        amount = money(inr * pack * (Decimal("1") + Decimal(index - 1) / 100))
        result.append({"key": f"v{index:02}", "code": f"SS-{sport[:2].upper()}-{key[:16]}-{index:02}",
                       "attributes": attributes, "prices": {"INR": amount, "USD": max(1, money(Decimal(amount) / DEMO_INR_PER_USD))},
                       "stock": 60 + index, "simulated": True})
    return result


def prepare_model(source, image):
    required = ("sport", "brand", "title", "sourceUrl", "capturedOn")
    if any(not source.get(field) for field in required):
        raise ValueError("Incomplete genuine model source")
    sport = source["sport"].casefold()
    if sport not in MINIMUMS:
        raise ValueError("Initial catalog supports cricket and football")
    date.fromisoformat(source["capturedOn"])
    key = source_key(source["sourceUrl"], source.get("recordId"))
    title = source["title"].strip()
    if len(title) > 200 or len(source["brand"]) > 120:
        raise ValueError("Source name exceeds catalog bounds")
    name = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()).strip("-")
    kind = source.get("equipmentType") or equipment(title, "equipment")
    if not isinstance(kind,str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}",kind):
        raise ValueError("Curated equipment type must be a bounded canonical name")
    model = source.get("model", title)
    return {"sourceKey": key, "sport": sport, "slug": name[:78] + "-" + key[:12], "brand": source["brand"],
            "model": model, "title": title, "equipmentType": kind,
            "description": f"{title} from {source['brand']}, listed for {sport} practice and play. Model and photograph are sourced; shop prices, stock and option ranges are simulated for this local learning store.",
            "source": {"url": source["sourceUrl"], "capturedOn": source["capturedOn"], "priceMinor": source.get("sourcePriceMinor"), "currency": source.get("sourceCurrency"),
                       **({"recordId": source["recordId"], "catalogYear": source["catalogYear"], "page": source["pdfImage"]["page"]} if source.get("recordId") else {})},
            "image": {**image, **({"pdfImage": source["pdfImage"]} if source.get("pdfImage") else {"url": source["imageUrl"]}), "altText": title},
            "sourcedFacts": source.get("sourcedFacts", {}),
            "variants": variants(key, sport, kind, source.get("fixtureBaseMinor", source.get("sourcePriceMinor")), source.get("fixtureCurrency", source.get("sourceCurrency")), source.get("fixtureOptions")),
            "reviewsPerProduct": 3 + int(key[0], 16) % 2}


def validate_manifest(manifest, minimums=None):
    if manifest.get("version") != 1 or not isinstance(manifest.get("products"), list):
        raise ValueError("Unsupported catalog manifest")
    products = manifest["products"]
    for fields in (("sourceKey",), ("slug",), ("sport", "brand", "model")):
        values = [tuple(str(p[field]).strip().casefold() for field in fields) for p in products]
        if len(values) != len(set(values)):
            raise ValueError("Duplicate source/model identity")
    codes = [v["code"] for p in products for v in p["variants"]]
    if len(codes) != len(set(codes)):
        raise ValueError("Duplicate sellable SKU code")
    photos = [p["image"]["sha256"] for p in products]
    if len(photos) != len(set(photos)):
        raise ValueError("One photograph is assigned to multiple distinct models")
    counts = Counter(p["sport"] for p in products)
    sku_counts = Counter()
    for product in products:
        if product["sourceKey"] != source_key(product["source"]["url"], product["source"].get("recordId")):
            raise ValueError("Source identity changed")
        if product["reviewsPerProduct"] not in (3, 4):
            raise ValueError("Each model needs three or four demo reviews")
        for variant in product["variants"]:
            if variant.get("simulated") is not True or type(variant["stock"]) is not int or variant["stock"] <= 0:
                raise ValueError("Invalid simulated initial stock")
            if set(variant["prices"]) != {"INR", "USD"} or any(type(amount) is not int or amount <= 0 for amount in variant["prices"].values()):
                raise ValueError("Every SKU needs positive integer INR/USD prices")
        sku_counts[product["sport"]] += len(product["variants"])
    for sport, (models, skus) in (MINIMUMS if minimums is None else minimums).items():
        if counts[sport] < models or sku_counts[sport] < skus:
            raise ValueError(f"{sport} needs at least {models} genuine models and {skus} sellable variants")
    return {sport: {"products": count, "skus": sku_counts[sport]} for sport, count in counts.items()}
