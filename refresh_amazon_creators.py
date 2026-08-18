"""Refresh existing Amazon offers through the official Amazon Creators API.

The integration is deliberately conservative: it only updates Amazon offers that
already exist in the PriceVichar catalog. Missing credentials and Amazon's 403
eligibility response are treated as safe skips so the daily catalog job continues
without deleting previously verified data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


TOKEN_ENDPOINTS = {
    "3.1": "https://api.amazon.com/auth/o2/token",
    "3.2": "https://api.amazon.co.uk/auth/o2/token",
    "3.3": "https://api.amazon.co.jp/auth/o2/token",
}
CATALOG_ENDPOINT = "https://creatorsapi.amazon/catalog/v1/getItems"
MARKETPLACE = "www.amazon.in"
DEFAULT_PARTNER_TAG = "bestdaam0a-21"
RESOURCES = [
    "images.primary.large",
    "itemInfo.title",
    "offersV2.listings.price",
    "offersV2.listings.availability",
]


class EligibilityError(RuntimeError):
    """Amazon account is authenticated but not currently catalog-eligible."""


def extract_asin(url: str) -> str | None:
    for pattern in (r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)",):
        match = re.search(pattern, url or "", re.IGNORECASE)
        if match:
            return match.group(1).upper()
    query = parse_qs(urlparse(url or "").query)
    for key in ("asin", "ASIN"):
        value = query.get(key)
        if value and re.fullmatch(r"[A-Z0-9]{10}", value[0], re.IGNORECASE):
            return value[0].upper()
    return None


def request_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        if error.code == 403 and "eligibility" in body.lower():
            raise EligibilityError(body) from error
        raise RuntimeError(f"Amazon API returned HTTP {error.code}: {body[:300]}") from error
    except URLError as error:
        raise RuntimeError(f"Amazon API network error: {error.reason}") from error


def get_access_token(credential_id: str, credential_secret: str, version: str) -> str:
    endpoint = TOKEN_ENDPOINTS.get(version)
    if not endpoint:
        raise ValueError(f"Unsupported Amazon credential version: {version}")
    response = request_json(
        endpoint,
        {
            "grant_type": "client_credentials",
            "client_id": credential_id,
            "client_secret": credential_secret,
            "scope": "creatorsapi::default",
        },
        {"Content-Type": "application/json"},
    )
    token = response.get("access_token")
    if not token:
        raise RuntimeError("Amazon token response did not contain an access token")
    return token


def get_items(access_token: str, partner_tag: str, asins: list[str]) -> list[dict]:
    response = request_json(
        CATALOG_ENDPOINT,
        {
            "itemIds": asins,
            "itemIdType": "ASIN",
            "marketplace": MARKETPLACE,
            "partnerTag": partner_tag,
            "resources": RESOURCES,
        },
        {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-marketplace": MARKETPLACE,
        },
    )
    container = response.get("itemsResult") or response.get("itemResults") or {}
    return container.get("items") or []


def item_offer(item: dict) -> tuple[float, str] | None:
    listings = ((item.get("offersV2") or {}).get("listings") or [])
    for listing in listings:
        availability = (listing.get("availability") or {}).get("type", "")
        availability = re.sub(r"[^a-z]", "", availability.lower())
        money = (listing.get("price") or {}).get("money") or {}
        if availability == "outofstock":
            continue
        try:
            amount = float(money.get("amount"))
        except (TypeError, ValueError):
            continue
        if money.get("currency") == "INR":
            return amount, item.get("detailPageURL") or ""
    return None


def refresh_catalog(products: list[dict], items: list[dict], checked_at: str) -> int:
    by_asin = {item.get("asin", "").upper(): item for item in items}
    updates = 0
    for product in products:
        for offer in product.get("prices", []):
            if str(offer.get("store", "")).lower() != "amazon":
                continue
            asin = extract_asin(offer.get("url", ""))
            parsed = item_offer(by_asin.get(asin, {})) if asin else None
            if not parsed:
                continue
            price, detail_url = parsed
            normalized_price = int(price) if price.is_integer() else price
            if offer.get("price") != normalized_price or detail_url:
                offer["price"] = normalized_price
                if detail_url:
                    offer["url"] = detail_url
                offer["checkedAt"] = checked_at
                updates += 1
    return updates


def write_catalog(path: Path, products: list[dict]) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(products, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    credential_id = os.environ.get("AMAZON_CREATORS_CREDENTIAL_ID")
    credential_secret = os.environ.get("AMAZON_CREATORS_CREDENTIAL_SECRET")
    if not credential_id or not credential_secret:
        print("Amazon Creators credentials missing: keeping existing Amazon offers.")
        return 0

    site_dir = Path(os.environ.get("BESTDAAM_SITE_DIR", "../bestdaam-price")).resolve()
    catalog_path = site_dir / "data" / "products.json"
    products = json.loads(catalog_path.read_text(encoding="utf-8"))

    offer_asins = sorted(
        {
            asin
            for product in products
            for offer in product.get("prices", [])
            if str(offer.get("store", "")).lower() == "amazon"
            if (asin := extract_asin(offer.get("url", "")))
        }
    )
    if not offer_asins:
        print("No existing Amazon ASINs found: nothing to refresh.")
        return 0

    try:
        token = get_access_token(
            credential_id,
            credential_secret,
            os.environ.get("AMAZON_CREATORS_CREDENTIAL_VERSION", "3.2"),
        )
        items = []
        partner_tag = os.environ.get("AMAZON_ASSOCIATE_TAG", DEFAULT_PARTNER_TAG)
        for start in range(0, len(offer_asins), 10):
            items.extend(get_items(token, partner_tag, offer_asins[start : start + 10]))
    except EligibilityError:
        print(
            "Amazon Creators authentication works, but catalog access is not yet "
            "eligible. Existing Amazon offers were preserved."
        )
        return 0
    except (RuntimeError, ValueError) as error:
        print(f"Amazon Creators refresh skipped safely: {error}")
        return 0

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    updates = refresh_catalog(products, items, checked_at)
    if updates:
        write_catalog(catalog_path, products)
    print(
        f"Amazon Creators checked {len(offer_asins)} ASINs; "
        f"refreshed {updates} existing offers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
