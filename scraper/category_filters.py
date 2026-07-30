import re


WIRED_EARPHONE_EXCLUSIONS = (
    "bluetooth",
    "neckband",
    "true wireless",
    "tws",
    "wireless",
)

SAMSUNG_BUDS_EXCLUSIONS = (
    "case",
    "cover",
    "compatible",
    "eartip",
    "protector",
    "refurbished",
    "renewed",
    "replacement",
    "skin",
)


def product_belongs_to_category(product, category_name):
    name = str(product.get("name", "")).lower()
    normalized_name = re.sub(r"[^a-z0-9]+", " ", name)

    if category_name == "wired_earphones":
        return not any(
            excluded_term in normalized_name
            for excluded_term in WIRED_EARPHONE_EXCLUSIONS
        )

    if category_name == "samsung_buds":
        official_name = re.sub(
            r"^sponsored\s+ad\s+",
            "",
            normalized_name,
        )
        is_samsung_buds = (
            "buds" in normalized_name
            and official_name.startswith("samsung ")
        )
        is_accessory = any(
            excluded_term in normalized_name
            for excluded_term in SAMSUNG_BUDS_EXCLUSIONS
        )
        return is_samsung_buds and not is_accessory

    return True
