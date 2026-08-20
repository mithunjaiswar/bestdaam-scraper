import json
import os
from pathlib import Path
import re
import subprocess
from difflib import SequenceMatcher
from urllib.parse import urlparse

import requests

from database.db import Database
from scraper.browser import SyncBrowserManager
from scraper.paginator import scrape_top_products


BASE_URL = "https://www.flipkart.com"
RESULTS_FILE = Path("output/product_request_results.json")
KEYCHAIN_SERVICE = "bestdaam-product-requests-token"
IGNORED_TOKENS = {
    "buy",
    "online",
    "best",
    "price",
    "india",
    "flipkart",
    "amazon",
    "with",
    "for",
    "and",
    "the",
}


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def search_label(request_item):
    label = clean_text(request_item.get("label"))

    if label:
        return label

    query = clean_text(request_item.get("query"))

    try:
        parsed = urlparse(query)
        product_path = parsed.path.split("/p/")[0]
        slug = [part for part in product_path.split("/") if part][-1]
        return slug.replace("-", " ")
    except (ValueError, IndexError):
        return query


def tokens(value):
    return [
        token
        for token in re.sub(r"[^a-z0-9]+", " ", value.lower()).split()
        if len(token) > 1 and token not in IGNORED_TOKENS
    ]


def match_score(candidate_name, requested_label):
    requested = tokens(requested_label)
    candidate = set(tokens(candidate_name))

    if not requested or not candidate:
        return 0

    matched = sum(
        1
        for token in requested
        if any(
            token == candidate_token
            or (
                len(token) >= 4
                and (
                    token.startswith(candidate_token)
                    or candidate_token.startswith(token)
                    or SequenceMatcher(
                        None,
                        token,
                        candidate_token,
                    ).ratio()
                    >= 0.82
                )
            )
            for candidate_token in candidate
        )
    )

    return matched / len(requested)


def normalized_name(value):
    return re.sub(r"[^a-z0-9]+", " ", clean_text(value).lower()).strip()


def is_reliable_match(candidate_name, requested_label, score=None):
    """Accept strong token matches and near-identical titles with extra variants.

    Flipkart sometimes omits suffixes such as colour and pack size from the
    visible search-card title. The full-title comparison prevents those exact
    products from being rejected while keeping unrelated short matches out.
    """
    score = match_score(candidate_name, requested_label) if score is None else score
    if score >= 0.65:
        return True

    candidate = normalized_name(candidate_name)
    requested = normalized_name(requested_label)
    if len(candidate) < 24 or len(requested) < 24:
        return False
    return SequenceMatcher(None, candidate, requested).ratio() >= 0.82


def infer_category(name):
    value = name.lower()
    rules = [
        ("wired_earphones", ("wired earphone", "3.5mm", "type c earphone")),
        ("earbuds", ("earbud", "tws", "airdopes")),
        ("headphones", ("headphone", "neckband", "headset")),
        (
            "mens_clothing",
            (
                "shirt",
                "t shirt",
                "tshirt",
                "jeans",
                "trouser",
                "kurta",
                "men clothing",
            ),
        ),
        ("iphone", ("iphone",)),
        ("laptops", ("laptop", "notebook", "macbook")),
        ("smartwatches", ("smartwatch", "smart watch")),
        ("televisions", ("television", "smart tv", " qled", " oled")),
        ("speakers", ("speaker", "soundbar")),
        ("tablets", ("tablet", "ipad")),
        ("cameras", ("camera", "drone")),
        ("mobiles", ("mobile", "smartphone", "phone")),
    ]

    for category, keywords in rules:
        if any(keyword in value for keyword in keywords):
            return category

    return "requested_products"


def api_request(method, params):
    api_url = os.environ.get("PRODUCT_REQUESTS_API_URL", "").strip()

    if not api_url:
        raise RuntimeError("PRODUCT_REQUESTS_API_URL missing")

    if method == "GET":
        response = requests.get(
            api_url,
            params=params,
            timeout=60,
        )
    else:
        response = requests.post(
            api_url,
            data=params,
            timeout=60,
        )

    response.raise_for_status()
    return response.json()


def get_api_token():
    token = os.environ.get("PRODUCT_REQUESTS_API_TOKEN", "").strip()

    if token:
        return token

    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def load_pending_requests():
    token = get_api_token()

    if not token:
        raise RuntimeError("PRODUCT_REQUESTS_API_TOKEN missing")

    response = api_request("GET", {"action": "list", "token": token})

    if response.get("success") != 1:
        raise RuntimeError(
            f"Product request API error: {response.get('error', 'unknown')}"
        )

    return [
        item
        for item in response.get("data", [])
        if clean_text(item.get("source")).lower() != "setup-test"
    ]


def update_request(request_id, status, result_url=""):
    token = get_api_token()
    return api_request(
        "POST",
        {
            "action": "update",
            "token": token,
            "id": request_id,
            "status": status,
            "result_url": result_url,
        },
    )


def process_pending_requests():
    pending = load_pending_requests()

    if not pending:
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_FILE.write_text("[]", encoding="utf-8")
        print("No pending product requests.")
        return []

    browser_manager = SyncBrowserManager()
    database = Database("products.db")
    processed = []

    try:
        page = browser_manager.start()

        for index, request_item in enumerate(pending, start=1):
            label = search_label(request_item)
            print(
                f"\n[{index}/{len(pending)}] Product request: {label}"
            )

            candidates = scrape_top_products(
                page=page,
                base_url=BASE_URL,
                category=label,
                limit=10,
            )
            ranked = sorted(
                candidates,
                key=lambda product: match_score(product.get("name", ""), label),
                reverse=True,
            )
            best = ranked[0] if ranked else None
            score = (
                match_score(best.get("name", ""), label)
                if best
                else 0
            )

            if not best or not is_reliable_match(
                best.get("name", ""), label, score
            ):
                print(
                    f"Needs review: reliable match nahi mila "
                    f"(score={score:.2f})."
                )
                processed.append(
                    {
                        "id": request_item["id"],
                        "status": "Needs Review",
                        "result_url": "",
                    }
                )
                continue

            # Requested items get a dedicated bucket so a full 100-item
            # category cannot silently push the requested item out of export.
            best["category"] = "requested_products"
            best["source"] = "flipkart"
            database.insert_product(best)
            processed.append(
                {
                    "id": request_item["id"],
                    "status": "Added",
                    "result_url": best["url"],
                }
            )
            print(
                f"Matched: {best['name']} (score={score:.2f})"
            )
    finally:
        database.close()
        browser_manager.close()

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(
        json.dumps(processed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return processed


if __name__ == "__main__":
    process_pending_requests()
