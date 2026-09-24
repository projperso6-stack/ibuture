import os
import re
import json
import html
from bs4 import BeautifulSoup
from collections import Counter

BASE = "site/de/products"
OUTPUT = "products_sample_v4.json"
LIMIT = 200


def clean_text(value):
    if not value:
        return ""
    soup = BeautifulSoup(str(value), "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def clean_html(value):
    if not value:
        return ""
    soup = BeautifulSoup(str(value), "html.parser")

    # Supprimer scripts/styles éventuels
    for tag in soup(["script", "style"]):
        tag.decompose()

    return str(soup).strip()


def language_score(text, lang):
    """
    Score très simple pour déterminer si un texte semble correspondre
    à la langue de la page.
    """
    if not text:
        return 0

    text = clean_text(text).lower()

    words = {
        "de": [
            "und", "der", "die", "das", "für", "mit", "nicht",
            "saugkraft", "staubsauger", "akku", "reinigung",
            "zubehör", "filter", "bürste"
        ],
        "fr": [
            "et", "pour", "avec", "les", "des", "une", "dans",
            "aspirateur", "puissance", "nettoyage", "batterie"
        ],
        "en": [
            "the", "and", "for", "with", "this", "your",
            "vacuum", "cleaning", "power", "battery", "brush"
        ],
        "it": [
            "il", "la", "per", "con", "una", "della",
            "aspirapolvere", "pulizia", "batteria"
        ],
        "es": [
            "el", "la", "para", "con", "una", "los",
            "aspiradora", "limpieza", "batería"
        ]
    }

    return sum(text.count(" " + w + " ") for w in words.get(lang, []))


def detect_locale(path):
    parts = path.replace("\\", "/").split("/")

    for p in parts:
        if re.fullmatch(r"[a-z]{2}(?:-[a-z]{2})?", p.lower()):
            return p.lower().split("-")[0]

    return None


def extract_json_ld(soup):
    results = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        if isinstance(data, list):
            results.extend(data)
        else:
            results.append(data)

    return results


def find_product_json_ld(jsonlds):
    candidates = []

    def inspect(obj):
        if not isinstance(obj, dict):
            return

        typ = obj.get("@type", "")

        if isinstance(typ, list):
            types = typ
        else:
            types = [typ]

        if any(t in ["Product", "ProductGroup"] for t in types):
            candidates.append(obj)

    for item in jsonlds:
        inspect(item)

        if isinstance(item, dict) and "@graph" in item:
            for obj in item["@graph"]:
                inspect(obj)

    return candidates


def extract_xcotton(soup):
    script = soup.find("script", id="xcotton_pp_variants")

    if not script:
        return None

    raw = script.string or script.get_text()

    if not raw:
        return None

    # Le script peut contenir directement du JSON
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Tentative de récupération JSON dans le script
    match = re.search(r"\{.*\}", raw, re.S)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return None


def get_currency(soup, html_source):
    # 1. storefrontCurrency
    patterns = [
        r"storefrontCurrency['\"]?\s*[:=]\s*['\"]([A-Z]{3})",
        r'"currency"\s*:\s*"([A-Z]{3})"',
        r"'currency'\s*:\s*'([A-Z]{3})'"
    ]

    for pattern in patterns:
        m = re.search(pattern, html_source, re.I)
        if m:
            return m.group(1).upper()

    # 2. meta
    meta = soup.find("meta", attrs={"property": "product:price:currency"})
    if meta and meta.get("content"):
        return meta["content"].upper()

    # 3. ShopifyAnalytics
    m = re.search(
        r"ShopifyAnalytics\.meta.*?currency['\"]?\s*:\s*['\"]([A-Z]{3})",
        html_source,
        re.I | re.S
    )

    if m:
        return m.group(1).upper()

    # 4. JSON-LD
    return None


def parse_price(value):
    if value is None:
        return None

    try:
        if isinstance(value, (int, float)):
            return round(float(value), 2)

        value = str(value).strip()

        # Shopify stocke généralement les prix en centimes
        if re.fullmatch(r"\d+", value):
            return round(int(value) / 100, 2)

        value = value.replace(",", ".")

        return float(value)

    except Exception:
        return None


def extract_variants(data):
    variants = []

    if not data:
        return variants

    for v in data.get("variants", []) or []:
        variants.append({
            "id": v.get("id"),
            "sku": v.get("sku"),
            "title": v.get("title"),
            "name": v.get("name"),
            "option1": v.get("option1"),
            "option2": v.get("option2"),
            "option3": v.get("option3"),
            "options": v.get("options"),
            "price": parse_price(v.get("price")),
            "compare_at_price": parse_price(v.get("compare_at_price")),
            "available": v.get("available"),
            "requires_shipping": v.get("requires_shipping"),
            "taxable": v.get("taxable"),
            "barcode": v.get("barcode"),
            "weight": v.get("weight"),
            "featured_image": v.get("featured_image"),
            "featured_media": v.get("featured_media"),
            "quantity_rule": v.get("quantity_rule"),
        })

    return variants


def extract_images(data):
    images = []

    if not data:
        return images

    for image in data.get("images", []) or []:
        if isinstance(image, str):
            images.append(image)
        elif isinstance(image, dict):
            src = image.get("src") or image.get("url")
            if src:
                images.append(src)

    # dédoublonnage
    return list(dict.fromkeys(images))


def get_description_sources(soup, data, product_jsonlds, lang):
    candidates = []

    # Shopify original
    shopify_description = ""
    if data:
        shopify_description = data.get("description") or ""

    if shopify_description:
        candidates.append({
            "source": "shopify_xcotton",
            "html": clean_html(shopify_description),
            "text": clean_text(shopify_description),
            "score": language_score(shopify_description, lang)
        })

    # JSON-LD
    for obj in product_jsonlds:
        desc = obj.get("description")

        if desc:
            candidates.append({
                "source": "jsonld",
                "html": clean_html(desc),
                "text": clean_text(desc),
                "score": language_score(desc, lang)
            })

    # Description visible courte
    selectors = [
        ".product-info__description",
        ".product__description",
        "[class*='product-description']",
        "[class*='product__description']"
    ]

    for selector in selectors:
        for element in soup.select(selector):
            text = element.get_text(" ", strip=True)

            if text:
                candidates.append({
                    "source": selector,
                    "html": clean_html(str(element)),
                    "text": clean_text(str(element)),
                    "score": language_score(text, lang)
                })

    return candidates


def choose_description(candidates, lang):
    if not candidates:
        return None

    # Éliminer les descriptions minuscules si une vraie description existe
    substantial = [
        c for c in candidates
        if len(c["text"]) >= 150
    ]

    if not substantial:
        substantial = candidates

    # Score :
    # langue locale prioritaire
    # longueur ensuite
    # JSON-LD légèrement favorisé si langue locale
    def ranking(c):
        language = c["score"]

        source_bonus = 0

        if c["source"] == "jsonld" and language > 0:
            source_bonus = 100

        if c["source"] == "shopify_xcotton":
            source_bonus += 20

        return (
            language * 1000 + source_bonus,
            len(c["text"])
        )

    return max(substantial, key=ranking)


def extract_short_description(soup, data, product_jsonlds):
    # priorité description visible courte
    selectors = [
        ".product-info__description",
        ".product__description"
    ]

    for selector in selectors:
        el = soup.select_one(selector)

        if el:
            text = clean_text(str(el))

            if 10 <= len(text) <= 1000:
                return text

    # JSON-LD
    for obj in product_jsonlds:
        desc = clean_text(obj.get("description"))

        if 10 <= len(desc) <= 1000:
            return desc

    # Shopify
    if data:
        desc = clean_text(data.get("description"))

        if 10 <= len(desc) <= 1000:
            return desc

    return ""


def extract_faq(soup):
    faq = []

    # FAQPage JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()

        try:
            data = json.loads(raw)
        except Exception:
            continue

        objects = data if isinstance(data, list) else [data]

        for obj in objects:
            if not isinstance(obj, dict):
                continue

            if obj.get("@type") == "FAQPage":
                for item in obj.get("mainEntity", []):
                    question = item.get("name", "")

                    answer = item.get("acceptedAnswer", {})
                    answer = answer.get("text", "") if isinstance(answer, dict) else ""

                    if question and answer:
                        faq.append({
                            "question": clean_text(question),
                            "answer_html": clean_html(answer),
                            "answer_text": clean_text(answer)
                        })

    return faq


def classify_product(variants, options):
    if len(variants) > 1:
        return "variable"

    if len(variants) == 0:
        return "simple"

    if options == ["Title"]:
        return "simple"

    if variants[0].get("title") == "Default Title":
        return "simple"

    return "simple"


def extract_product(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    soup = BeautifulSoup(raw, "html.parser")

    lang = detect_locale(path) or "en"

    data = extract_xcotton(soup)

    jsonlds = extract_json_ld(soup)
    product_jsonlds = find_product_json_ld(jsonlds)

    title = ""

    if data:
        title = data.get("title") or ""

    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else ""

    if not title and product_jsonlds:
        title = product_jsonlds[0].get("name", "")

    handle = data.get("handle") if data else None

    if not handle:
        handle = os.path.basename(os.path.dirname(path))

    candidates = get_description_sources(
        soup,
        data,
        product_jsonlds,
        lang
    )

    chosen = choose_description(candidates, lang)

    description_html = chosen["html"] if chosen else ""
    description_text = chosen["text"] if chosen else ""

    short_description = extract_short_description(
        soup,
        data,
        product_jsonlds
    )

    meta = soup.find("meta", attrs={"name": "description"})
    meta_description = meta.get("content", "") if meta else ""

    variants = extract_variants(data)

    images = extract_images(data)

    options = data.get("options", []) if data else []

    product_type = classify_product(
        variants,
        options
    )

    price_values = [
        v["price"]
        for v in variants
        if v["price"] is not None
    ]

    compare_values = [
        v["compare_at_price"]
        for v in variants
        if v["compare_at_price"] is not None
    ]

    price = min(price_values) if price_values else (
        parse_price(data.get("price")) if data else None
    )

    compare_at_price = max(compare_values) if compare_values else (
        parse_price(data.get("compare_at_price")) if data else None
    )

    regular_price = compare_at_price if (
        compare_at_price and price and compare_at_price > price
    ) else price

    sale_price = price if (
        compare_at_price and price and compare_at_price > price
    ) else None

    currency = get_currency(soup, raw)

    category = ""

    if product_jsonlds:
        category = product_jsonlds[0].get("category") or ""

    if not category and data:
        category = data.get("type") or ""

    tags = data.get("tags", []) if data else []

    vendor = data.get("vendor") if data else ""

    faq = extract_faq(soup)

    anomalies = []

    if not title:
        anomalies.append("missing_title")

    if not description_text:
        anomalies.append("missing_description")

    if not images:
        anomalies.append("missing_images")

    if not category:
        anomalies.append("missing_category")

    if not currency:
        anomalies.append("missing_currency")

    if product_type == "variable" and len(variants) == 0:
        anomalies.append("variable_without_variants")

    if any(
        v["price"] is None
        for v in variants
    ):
        anomalies.append("variant_missing_price")

    skus = [
        v["sku"]
        for v in variants
        if v.get("sku")
    ]

    return {
        "product_id": data.get("id") if data else None,
        "handle": handle,
        "url": "/" + "/".join(
            path.split("/")[2:]
        ).replace("/index.html", "/"),
        "locale": lang,

        "title": title,
        "vendor": vendor,
        "type": data.get("type") if data else "",
        "category": category,
        "tags": tags,

        "description_html": description_html,
        "description_text": description_text,
        "description_source": chosen["source"] if chosen else None,

        "short_description": short_description,
        "meta_description": meta_description,

        "currency": currency,

        "price": price,
        "regular_price": regular_price,
        "sale_price": sale_price,
        "compare_at_price": compare_at_price,

        "product_type": product_type,
        "options": options,
        "variants": variants,

        "images": images,

        "faq": faq,

        "sku_count": len(skus),

        "json_ld": product_jsonlds,

        "anomalies": anomalies
    }


def main():
    files = []

    for root, dirs, filenames in os.walk(BASE):
        for filename in filenames:
            if filename.lower() == "index.html":
                files.append(os.path.join(root, filename))

    files.sort()

    print(f"Produits trouvés : {len(files)}")
    print(f"Extraction de {min(LIMIT, len(files))} produits")
    print()

    results = []
    errors = []

    for i, path in enumerate(files[:LIMIT], 1):
        try:
            product = extract_product(path)
            results.append(product)

            print(
                f"[{i:03d}/{min(LIMIT,len(files)):03d}] "
                f"{product['handle']} | "
                f"{product['product_type']} | "
                f"{product['currency']} | "
                f"{len(product['variants'])} var | "
                f"{len(product['images'])} img | "
                f"desc={len(product['description_text'])}"
            )

        except Exception as e:
            errors.append({
                "file": path,
                "error": str(e)
            })

            print(f"[ERREUR] {path}: {e}")

    # Statistiques
    currencies = Counter(
        p["currency"] for p in results
    )

    types = Counter(
        p["product_type"] for p in results
    )

    missing_desc = sum(
        not p["description_text"]
        for p in results
    )

    missing_images = sum(
        not p["images"]
        for p in results
    )

    missing_category = sum(
        not p["category"]
        for p in results
    )

    anomalies = Counter()

    for p in results:
        for anomaly in p["anomalies"]:
            anomalies[anomaly] += 1

    output = {
        "metadata": {
            "extractor": "extract_products_v4.py",
            "limit": LIMIT,
            "products_extracted": len(results),
            "errors": len(errors),

            "currencies": dict(currencies),
            "product_types": dict(types),

            "missing_descriptions": missing_desc,
            "missing_images": missing_images,
            "missing_categories": missing_category,

            "anomalies": dict(anomalies)
        },

        "errors": errors,

        "products": results
    }

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("RAPPORT V4")
    print("=" * 60)

    print(f"Produits extraits : {len(results)}")
    print(f"Erreurs           : {len(errors)}")
    print(f"Devises           : {dict(currencies)}")
    print(f"Types             : {dict(types)}")
    print(f"Sans description  : {missing_desc}")
    print(f"Sans images       : {missing_images}")
    print(f"Sans catégorie    : {missing_category}")
    print(f"Anomalies         : {dict(anomalies)}")

    print()
    print(f"Fichier créé : {OUTPUT}")


if __name__ == "__main__":
    main()
