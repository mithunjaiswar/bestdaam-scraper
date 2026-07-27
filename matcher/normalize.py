import re
import unicodedata


def normalize_product_name(name: str) -> str:
    if not name:
        return ""

    name = str(name)
    name = unicodedata.normalize("NFKD", name)
    name = name.lower()

    name = name.replace("sponsored ad -", " ")
    name = name.replace("sponsored", " ")

    name = re.sub(r"(\d+)\s*gb", r"\1gb", name)
    name = re.sub(r"(\d+)\s*tb", r"\1tb", name)

    name = name.replace("″", " inch ")
    name = name.replace('"', " inch ")
    name = name.replace(":", " ")
    name = name.replace("|", " ")
    name = name.replace(",", " ")
    name = name.replace("(", " ")
    name = name.replace(")", " ")

    name = re.sub(r"[^a-z0-9\s]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name


def extract_storage(name: str) -> str | None:
    normalized = normalize_product_name(name)

    match = re.search(r"\b(\d+gb|\d+tb)\b", normalized)

    if match:
        return match.group(1)

    return None


def extract_brand(name: str) -> str | None:
    normalized = normalize_product_name(name)

    brand_aliases = {
        "goboult": "boult",
        "fire boltt": "fire boltt",
        "amazon basics": "amazon basics",
    }

    brands = {
        "apple", "samsung", "oneplus", "redmi", "xiaomi", "iqoo",
        "realme", "oppo", "vivo", "motorola", "nothing", "google",
        "nokia", "hp", "dell", "lenovo", "asus", "acer", "reliance",
        "vw", "lg", "sony", "boat", "jbl", "noise", "boult", "ptron",
        "zebronics", "skullcandy", "sennheiser", "philips", "bose",
        "marshall", "portronics", "mivi", "crossbeats", "fastrack",
        "amazfit", "dji", "canon", "nikon", "fujifilm", "panasonic",
        "kodak", "tcl", "mi", "hisense", "thomson", "infinix",
    }

    # Brand is expected at the beginning of a marketplace title. Searching the
    # whole title misclassifies phrases such as "noise cancellation" as Noise.
    for alias, canonical in brand_aliases.items():
        if normalized == alias or normalized.startswith(f"{alias} "):
            return canonical

    first_token = normalized.split()[0] if normalized.split() else ""

    if first_token in brands:
        return first_token

    return None


def extract_model_tokens(name: str) -> set[str]:
    normalized = normalize_product_name(name)
    tokens = set()

    ignored = {
        "3mm",
        "5mm",
        "4k",
        "5g",
        "1080p",
        "720p",
    }

    for token in normalized.split():
        if token in ignored:
            continue

        if re.fullmatch(
            r"\d+(?:gb|tb|mb|mah|hz|khz|w|wh|mp|inch|cm|h|hr|hrs|ms|mic|mm|db)",
            token,
        ):
            continue

        if re.fullmatch(r"(?:i[3579]|r[3579]|\d+(?:st|nd|rd|th))", token):
            continue

        # Model identifiers normally mix letters and numbers: C100SI, Airdopes141.
        if (
            len(token) >= 3
            and re.search(r"[a-z]", token)
            and re.search(r"\d", token)
        ):
            tokens.add(token)

    return tokens


def extract_laptop_family(name: str) -> str | None:
    normalized = normalize_product_name(name)
    families = (
        "aspire",
        "chromebook",
        "envy",
        "ideapad",
        "inspiron",
        "latitude",
        "legion",
        "macbook",
        "nitro",
        "omen",
        "pavilion",
        "swift",
        "thinkbook",
        "thinkpad",
        "tuf",
        "victus",
        "vivobook",
        "vostro",
        "yoga",
    )

    for family in families:
        if re.search(rf"\b{family}\b", normalized):
            return family

    return None


def extract_product_line(name: str, brand: str | None) -> tuple[str, ...]:
    normalized = normalize_product_name(name)
    tokens = normalized.split()

    brand_tokens = (brand or "").split()

    if brand_tokens and tokens[:len(brand_tokens)] == brand_tokens:
        tokens = tokens[len(brand_tokens):]

    # Common brand repetition in Zebronics titles.
    if brand == "zebronics" and tokens[:1] == ["zeb"]:
        tokens = tokens[1:]

    stop_words = {
        "active", "bluetooth", "camera", "earbuds", "earphone",
        "earphones", "headphone", "headphones", "headset", "in",
        "mirrorless", "mobile", "phone", "smart", "smartwatch", "speaker",
        "tws", "watch", "with", "wired", "wireless",
    }

    identity = []

    for token in tokens:
        if token in stop_words:
            break

        if re.fullmatch(
            r"\d+(?:gb|tb|mah|hz|khz|w|wh|mp|inch|cm|h|hr|hrs|ms|mic|mm|db)",
            token,
        ):
            break

        identity.append(token)

        if len(identity) >= 3:
            break

    return tuple(identity)


def extract_iphone_model(name: str) -> str | None:
    normalized = normalize_product_name(name)

    patterns = [
        r"\biphone\s+16\s+plus\b",
        r"\biphone\s+15\s+plus\b",
        r"\biphone\s+14\s+plus\b",
        r"\biphone\s+13\s+plus\b",
        r"\biphone\s+17e\b",
        r"\biphone\s+16e\b",
        r"\biphone\s+15e\b",
        r"\biphone\s+air\b",
        r"\biphone\s+17\b",
        r"\biphone\s+16\b",
        r"\biphone\s+15\b",
        r"\biphone\s+14\b",
        r"\biphone\s+13\b",
        r"\biphone\s+12\b",
        r"\biphone\s+11\b",
        r"\biphone\s+xr\b",
        r"\biphone\s+xs\b",
        r"\biphone\s+x\b",
        r"\biphone\s+se\b",
        r"\biphone\s+8\b",
        r"\biphone\s+7\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip()

    return None


def extract_tv_size(name: str) -> str | None:
    normalized = normalize_product_name(name)

    # 80 cm (32 inch)
    inch_match = re.search(r"\b(\d{2,3})\s*inch\b", normalized)
    if inch_match:
        return f"{inch_match.group(1)}inch"

    cm_match = re.search(r"\b(\d{2,3})\s*cm\b", normalized)
    if cm_match:
        cm = int(cm_match.group(1))

        # Common India TV size conversion
        cm_to_inch = {
            80: "32inch",
            81: "32inch",
            108: "43inch",
            109: "43inch",
            127: "50inch",
            139: "55inch",
            164: "65inch",
        }

        return cm_to_inch.get(cm, f"{cm}cm")

    return None


def extract_tv_resolution(name: str) -> str | None:
    normalized = normalize_product_name(name)

    if re.search(r"\bfull\s*hd\b", normalized):
        return "full_hd"

    if re.search(r"\bhd\s*ready\b", normalized):
        return "hd_ready"

    if re.search(r"\b4k\b|\bultra\s*hd\b|\buhd\b", normalized):
        return "4k"

    return None


def extract_year(name: str) -> str | None:
    normalized = normalize_product_name(name)

    match = re.search(r"\b(2024|2025|2026|2027)\b", normalized)

    if match:
        return match.group(1)

    return None


def looks_like_tv(name: str) -> bool:
    normalized = normalize_product_name(name)

    tv_words = [
        "tv",
        "television",
        "inch",
        "hd ready",
        "full hd",
        "4k",
        "ultra hd",
        "led",
        "qled",
        "oled",
    ]

    return any(word in normalized for word in tv_words)


def looks_like_phone(name: str) -> bool:
    normalized = normalize_product_name(name)

    phone_words = [
        "iphone",
        "galaxy",
        "redmi",
        "realme",
        "oneplus",
        "iqoo",
        "nokia",
        "mobile",
        "phone",
        "5g",
    ]

    return any(word in normalized for word in phone_words)
