import json
import os
import re
import subprocess
import time
from datetime import datetime

import requests


API_URL = "https://ekaro-api.affiliaters.in/api/converter/public"
SITE_DIR = os.path.expanduser(
    os.environ.get("BESTDAAM_SITE_DIR", "~/Desktop/bestdaam-price")
)
PRODUCTS_JSON = os.path.join(SITE_DIR, "data", "products.json")
BACKUP_DIR = "output/backups"

SLEEP_SECONDS = 1.5
SAVE_EVERY = 25
KEYCHAIN_SERVICE = "bestdaam-ekaro-api-token"


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def find_first_url(value):
    if isinstance(value, str):
        urls = re.findall(r"https?://[^\s\"'<>]+", value)

        if urls:
            return urls[0]

        return ""

    if isinstance(value, dict):
        for item in value.values():
            found = find_first_url(item)

            if found:
                return found

    if isinstance(value, list):
        for item in value:
            found = find_first_url(item)

            if found:
                return found

    return ""


def convert_url(original_url, token):
    payload = {
        "deal": original_url,
        "convert_option": "convert_only",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
    except Exception as error:
        print(f"Request failed: {error}")
        return ""

    if response.status_code != 200:
        print(f"API status error: {response.status_code}")
        print(response.text[:300])
        return ""

    try:
        data = response.json()
    except Exception:
        data = response.text

    if isinstance(data, dict):
        if data.get("success") == 1 and data.get("data"):
            return clean_text(data.get("data"))

        possible_url = find_first_url(data)

        if possible_url:
            return possible_url

    if isinstance(data, str):
        possible_url = find_first_url(data)

        if possible_url:
            return possible_url

    print("No affiliate URL found in response:")
    print(data)

    return ""


def save_products(products):
    with open(PRODUCTS_JSON, "w", encoding="utf-8") as file:
        json.dump(products, file, ensure_ascii=False, indent=2)


def get_api_token():
    token = os.environ.get("EKARO_API_TOKEN", "").strip()

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


def main():
    token = get_api_token()

    if not token:
        print("EKARO_API_TOKEN missing.")
        print("Save it in the Mac Keychain before the daily automation.")
        return

    if not os.path.exists(PRODUCTS_JSON):
        print(f"Products JSON not found: {PRODUCTS_JSON}")
        return

    with open(PRODUCTS_JSON, "r", encoding="utf-8") as file:
        products = json.load(file)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_path = os.path.join(
        BACKUP_DIR,
        "products_backup_before_ekaro_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    with open(backup_path, "w", encoding="utf-8") as file:
        json.dump(products, file, ensure_ascii=False, indent=2)

    pending_entries = []

    for product in products:
        for entry in product.get("prices", []):
            store = clean_text(entry.get("store")).lower()

            if store != "flipkart":
                continue

            original_url = clean_text(entry.get("url"))

            if not original_url:
                continue

            if entry.get("affiliateUrl"):
                continue

            pending_entries.append(
                {
                    "product_name": product.get("name", ""),
                    "entry": entry,
                    "url": original_url,
                }
            )

    print("=" * 80)
    print(f"Total products                 : {len(products)}")
    print(f"Pending Flipkart links to convert: {len(pending_entries)}")
    print(f"Backup saved                   : {backup_path}")
    print("=" * 80)

    applied_count = 0
    failed_count = 0

    for index, item in enumerate(pending_entries, start=1):
        product_name = item["product_name"]
        original_url = item["url"]

        print(f"[{index}/{len(pending_entries)}] Converting: {product_name[:70]}")

        affiliate_url = convert_url(original_url, token)

        if affiliate_url:
            item["entry"]["affiliateUrl"] = affiliate_url
            applied_count += 1
            print(f"  OK: {affiliate_url}")
        else:
            failed_count += 1
            print("  Failed")

        if index % SAVE_EVERY == 0:
            save_products(products)
            print(f"Progress saved after {index} links.")

        time.sleep(SLEEP_SECONDS)

    save_products(products)

    print("=" * 80)
    print(f"Affiliate links applied : {applied_count}")
    print(f"Failed links            : {failed_count}")
    print(f"Updated file            : {PRODUCTS_JSON}")
    print(f"Backup file             : {backup_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
