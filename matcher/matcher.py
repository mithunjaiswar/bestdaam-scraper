from rapidfuzz import fuzz

from matcher.normalize import (
    normalize_product_name,
    extract_brand,
    extract_storage,
    extract_iphone_model,
    extract_tv_size,
    extract_tv_resolution,
    extract_year,
    extract_model_tokens,
    extract_laptop_family,
    extract_product_line,
    looks_like_tv,
)


def extract_airpods_model(name: str) -> str:
    clean = normalize_product_name(name)

    if "airpods" not in clean:
        return ""

    if "max" in clean:
        return "airpods max"

    if "pro 3" in clean or "pro 3rd" in clean:
        return "airpods pro 3"

    if "pro 2" in clean or "pro 2nd" in clean:
        return "airpods pro 2"

    if "pro" in clean:
        return "airpods pro"

    if "airpods 4" in clean:
        return "airpods 4 anc" if "noise cancellation" in clean else "airpods 4"

    if "3rd generation" in clean or "3rd gen" in clean:
        return "airpods 3"

    if "2nd generation" in clean or "2nd gen" in clean:
        return "airpods 2"

    return "airpods"


def extract_samsung_buds_model(name: str) -> str:
    clean = normalize_product_name(name)

    if "buds" not in clean or (
        "samsung" not in clean and "galaxy" not in clean
    ):
        return ""

    model_patterns = (
        (("buds 4 pro", "buds4 pro"), "buds4 pro"),
        (("buds 4", "buds4"), "buds4"),
        (("buds 3 pro", "buds3 pro"), "buds3 pro"),
        (("buds 3 fe", "buds3 fe"), "buds3 fe"),
        (("buds 3", "buds3"), "buds3"),
        (("buds 2 pro", "buds2 pro"), "buds2 pro"),
        (("buds 2", "buds2"), "buds2"),
        (("buds fe",), "buds fe"),
        (("buds core",), "buds core"),
        (("buds pro",), "buds pro"),
        (("buds live",), "buds live"),
        (("buds plus", "buds +"), "buds plus"),
    )

    for aliases, model in model_patterns:
        if any(alias in clean for alias in aliases):
            return model

    return ""


def match_products(
    flipkart_name: str,
    amazon_name: str,
    threshold: float = 85.0,
    category: str = "",
):
    flipkart_clean = normalize_product_name(flipkart_name)
    amazon_clean = normalize_product_name(amazon_name)

    if not flipkart_clean or not amazon_clean:
        return False, 0.0

    flipkart_brand = extract_brand(flipkart_name)
    amazon_brand = extract_brand(amazon_name)

    if flipkart_brand and amazon_brand and flipkart_brand != amazon_brand:
        return False, 0.0

    flipkart_storage = extract_storage(flipkart_name)
    amazon_storage = extract_storage(amazon_name)

    if flipkart_storage and amazon_storage and flipkart_storage != amazon_storage:
        return False, 0.0

    # Mechanical-pencil lead titles vary heavily between marketplaces.
    # Size, grade and brand identify the requested consumable reliably.
    flipkart_is_05_4b_lead = (
        "lead" in flipkart_clean and "0 5mm" in flipkart_clean and "4b" in flipkart_clean
    )
    amazon_is_05_4b_lead = (
        "lead" in amazon_clean and "0 5mm" in amazon_clean and "4b" in amazon_clean
    )

    if flipkart_is_05_4b_lead or amazon_is_05_4b_lead:
        if not flipkart_is_05_4b_lead or not amazon_is_05_4b_lead:
            return False, 0.0

        lead_brands = {"pentel", "brustro"}
        shared_lead_brands = (
            set(flipkart_clean.split())
            & set(amazon_clean.split())
            & lead_brands
        )

        if (
            flipkart_brand
            and amazon_brand
            and flipkart_brand == amazon_brand
        ) or shared_lead_brands:
            return True, 100.0

        return False, 0.0

    # AirPods are Apple products but do not have an iPhone model/storage.
    # Compare their exact generation/family before applying iPhone rules.
    flipkart_airpods = extract_airpods_model(flipkart_name)
    amazon_airpods = extract_airpods_model(amazon_name)

    if flipkart_airpods or amazon_airpods:
        if not flipkart_airpods or not amazon_airpods:
            return False, 0.0

        if flipkart_airpods != amazon_airpods:
            return False, 0.0

        return True, 100.0

    flipkart_samsung_buds = extract_samsung_buds_model(flipkart_name)
    amazon_samsung_buds = extract_samsung_buds_model(amazon_name)

    if flipkart_samsung_buds or amazon_samsung_buds:
        if not flipkart_samsung_buds or not amazon_samsung_buds:
            return False, 0.0

        if flipkart_samsung_buds != amazon_samsung_buds:
            return False, 0.0

        return True, 100.0

    # =====================================================
    # APPLE IPHONE STRICT MATCHING
    # =====================================================
    if flipkart_brand == "apple" or amazon_brand == "apple":
        flipkart_iphone_model = extract_iphone_model(flipkart_name)
        amazon_iphone_model = extract_iphone_model(amazon_name)

        if not flipkart_iphone_model or not amazon_iphone_model:
            return False, 0.0

        if flipkart_iphone_model != amazon_iphone_model:
            return False, 0.0

        if not flipkart_storage or not amazon_storage:
            return False, 0.0

        if flipkart_storage != amazon_storage:
            return False, 0.0

        identity_1 = f"apple {flipkart_iphone_model} {flipkart_storage}"
        identity_2 = f"apple {amazon_iphone_model} {amazon_storage}"

        score = fuzz.ratio(identity_1, identity_2)

        return True, round(score, 2)

    # =====================================================
    # TV STRICT MATCHING
    # Same brand + same size + same resolution + same year if available
    # =====================================================
    if looks_like_tv(flipkart_name) or looks_like_tv(amazon_name):
        flipkart_size = extract_tv_size(flipkart_name)
        amazon_size = extract_tv_size(amazon_name)

        if not flipkart_size or not amazon_size:
            return False, 0.0

        if flipkart_size != amazon_size:
            return False, 0.0

        flipkart_resolution = extract_tv_resolution(flipkart_name)
        amazon_resolution = extract_tv_resolution(amazon_name)

        if flipkart_resolution and amazon_resolution:
            if flipkart_resolution != amazon_resolution:
                return False, 0.0

        flipkart_year = extract_year(flipkart_name)
        amazon_year = extract_year(amazon_name)

        if flipkart_year and amazon_year:
            if flipkart_year != amazon_year:
                return False, 0.0

        token_sort_score = fuzz.token_sort_ratio(flipkart_clean, amazon_clean)
        token_set_score = fuzz.token_set_ratio(flipkart_clean, amazon_clean)

        score = round((token_sort_score * 0.5) + (token_set_score * 0.5), 2)

        if score >= 88:
            return True, score

        return False, score

    if category == "laptops":
        flipkart_family = extract_laptop_family(flipkart_name)
        amazon_family = extract_laptop_family(amazon_name)

        if (
            flipkart_family
            and amazon_family
            and flipkart_family != amazon_family
        ):
            return False, 0.0

    # =====================================================
    # GENERAL MATCHING
    # =====================================================
    token_sort_score = fuzz.token_sort_ratio(flipkart_clean, amazon_clean)
    token_set_score = fuzz.token_set_ratio(flipkart_clean, amazon_clean)

    score = round((token_sort_score * 0.4) + (token_set_score * 0.6), 2)

    # Marketplace titles often add different marketing phrases around the
    # same model. Relax only when both sides identify the same known brand.
    relaxed_model_categories = {
        "cameras",
        "earbuds",
        "samsung_buds",
        "headphones",
        "mobiles",
        "smartwatches",
        "speakers",
        "wired_earphones",
        "requested_products",
    }

    same_known_brand = (
        flipkart_brand
        and amazon_brand
        and flipkart_brand == amazon_brand
    )
    flipkart_models = extract_model_tokens(flipkart_name)
    amazon_models = extract_model_tokens(amazon_name)
    flipkart_line = extract_product_line(flipkart_name, flipkart_brand)
    amazon_line = extract_product_line(amazon_name, amazon_brand)

    if (
        category in relaxed_model_categories
        and same_known_brand
        and flipkart_models
        and amazon_models
        and flipkart_models.isdisjoint(amazon_models)
    ):
        return False, score

    if (
        category in relaxed_model_categories
        and same_known_brand
        and flipkart_line
        and amazon_line
    ):
        compare_length = min(3, len(flipkart_line), len(amazon_line))

        if flipkart_line[:compare_length] != amazon_line[:compare_length]:
            return False, score

    if score >= threshold:
        return True, score

    if (
        category in relaxed_model_categories
        and
        same_known_brand
    ):
        if flipkart_models and amazon_models:
            if token_set_score >= 72:
                return True, round(token_set_score, 2)

        if token_set_score >= 88:
            return True, round(token_set_score, 2)

    return False, score


def is_same_product(name1: str, name2: str, threshold: float = 85.0):
    return match_products(name1, name2, threshold)
