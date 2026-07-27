import re


WIRED_EARPHONE_EXCLUSIONS = (
    "bluetooth",
    "neckband",
    "true wireless",
    "tws",
    "wireless",
)


def product_belongs_to_category(product, category_name):
    if category_name != "wired_earphones":
        return True

    name = str(product.get("name", "")).lower()
    normalized_name = re.sub(r"[^a-z0-9]+", " ", name)

    return not any(
        excluded_term in normalized_name
        for excluded_term in WIRED_EARPHONE_EXCLUSIONS
    )
