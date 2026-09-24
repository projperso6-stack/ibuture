import os
import re
import json
import csv
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURATION
# ============================================================

BASE = "/workspaces/ibuture/site/de/products"

# 0 = tous les produits
# Pour un test : 200
LIMIT = 200

OUTPUT_JSON = "/workspaces/ibuture/products_catalog_v6.json"
OUTPUT_CSV = "/workspaces/ibuture/products_catalog_v6.csv"

# ============================================================
# OUTILS
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = str(value)

    value = re.sub(r"\s+", " ", value)
    value = value.replace("\xa0", " ")

    return value.strip()


def clean_html(value):
    if not value:
        return ""

    soup = BeautifulSoup(value, "html.parser")

    # Retirer les éléments non pertinents
    for tag in soup([
        "script",
        "style",
        "noscript",
        "template"
    ]):
        tag.decompose()

    return clean_text(soup.get_text(" ", strip=True))


def normalize_url(url):
    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return "https://ibuture.com" + url

    return url


def money(value):
    """
    Shopify stocke généralement les prix en cents.
    Exemple :
    3866 -> 38.66
    """

    if value is None or value == "":
        return ""

    try:
        return round(float(value) / 100, 2)
    except Exception:
        return ""


def parse_json_script(soup, script_id=None, script_type=None):
    scripts = []

    if script_id:
        tag = soup.find("script", id=script_id)
        if tag:
            scripts.append(tag)

    elif script_type:
        scripts = soup.find_all("script", attrs={"type": script_type})

    result = []

    for tag in scripts:
        raw = tag.string or tag.get_text()

        if not raw:
            continue

        try:
            result.append(json.loads(raw))
        except Exception:
            continue

    return result


def find_product_json(soup):
    """
    Shopify / xcotton product data.
    """

    tag = soup.find("script", id="xcotton_pp_variants")

    if not tag:
        return {}

    raw = tag.string or tag.get_text()

    if not raw:
        return {}

    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_jsonld_products(soup):
    """
    Retourne les objets JSON-LD de type Product/ProductGroup.
    """

    objects = []

    scripts = soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    )

    for script in scripts:

        raw = script.string or script.get_text()

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        candidates = []

        if isinstance(data, list):
            candidates.extend(data)

        elif isinstance(data, dict):

            if isinstance(data.get("@graph"), list):
                candidates.extend(data["@graph"])

            else:
                candidates.append(data)

        for obj in candidates:

            if not isinstance(obj, dict):
                continue

            typ = obj.get("@type")

            if typ in ("Product", "ProductGroup"):
                objects.append(obj)

    return objects


def get_primary_jsonld(soup):
    products = get_jsonld_products(soup)

    if not products:
        return {}

    # Préférer ProductGroup
    for obj in products:
        if obj.get("@type") == "ProductGroup":
            return obj

    return products[0]


def get_meta(soup, name=None, prop=None):

    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag:
            return tag.get("content", "")

    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag:
            return tag.get("content", "")

    return ""


def get_currency(soup, jsonld=None):

    # 1. storefrontCurrency
    html = str(soup)

    patterns = [
        r"storefrontCurrency['\"]?\s*[:=]\s*['\"]([A-Z]{3})",
        r"currency['\"]?\s*[:=]\s*['\"]([A-Z]{3})",
    ]

    for pattern in patterns:
        m = re.search(pattern, html, re.I)
        if m:
            return m.group(1).upper()

    # 2. Meta Shopify
    currency = get_meta(
        soup,
        prop="product:price:currency"
    )

    if currency:
        return currency.upper()

    # 3. JSON-LD
    if isinstance(jsonld, dict):

        offers = jsonld.get("offers")

        if isinstance(offers, dict):
            currency = offers.get("priceCurrency")

            if currency:
                return str(currency).upper()

        elif isinstance(offers, list):

            for offer in offers:

                if isinstance(offer, dict):
                    currency = offer.get("priceCurrency")

                    if currency:
                        return str(currency).upper()

    # 4. ShopifyAnalytics
    m = re.search(
        r"ShopifyAnalytics\.meta.*?currency['\"]?\s*:\s*['\"]([A-Z]{3})",
        html,
        re.I | re.S
    )

    if m:
        return m.group(1).upper()

    return ""


def is_generic_description(text):

    if not text:
        return True

    text_lower = text.lower()

    forbidden = [
        "buture focuses on providing",
        "jump starters",
        "explore our product range",
        "shopify",
        "klarna",
        "loyalty",
        "cookie",
        "privacy policy",
        "customer service",
        "newsletter"
    ]

    for phrase in forbidden:
        if phrase in text_lower:
            return True

    return False


def find_description(soup, product_json, jsonld):

    candidates = []

    # --------------------------------------------------------
    # 1. xcotton
    # --------------------------------------------------------

    x_desc = product_json.get("description")

    if x_desc:
        text = clean_html(x_desc)

        if text and not is_generic_description(text):
            candidates.append(
                ("full", text, 100)
            )

    # --------------------------------------------------------
    # 2. JSON-LD
    # --------------------------------------------------------

    if jsonld:

        ld_desc = jsonld.get("description")

        if ld_desc:
            text = clean_html(ld_desc)

            if text and not is_generic_description(text):
                candidates.append(
                    ("full", text, 90)
                )

    # --------------------------------------------------------
    # 3. Descriptions HTML ciblées
    # --------------------------------------------------------

    selectors = [
        ".product-info__description",
        ".product__description",
        "[class*='product-description']",
        "[class*='product__description']",
        ".product-description",
    ]

    for selector in selectors:

        for tag in soup.select(selector):

            text = clean_html(str(tag))

            if (
                text
                and len(text) > 80
                and not is_generic_description(text)
            ):
                candidates.append(
                    ("full", text, 80)
                )

    # --------------------------------------------------------
    # 4. Meta description
    # --------------------------------------------------------

    meta = get_meta(soup, name="description")

    meta = clean_text(meta)

    if meta and not is_generic_description(meta):

        candidates.append(
            ("meta_fallback", meta, 40)
        )

    # --------------------------------------------------------
    # Choix
    # --------------------------------------------------------

    if not candidates:
        return "", "none"

    # Score + longueur raisonnable
    candidates.sort(
        key=lambda x: (x[2], min(len(x[1]), 10000)),
        reverse=True
    )

    source, text, _ = candidates[0]

    # Eviter les descriptions absurdement énormes
    if len(text) > 30000:
        text = text[:30000]

    return text, source


def find_short_description(soup, title):

    # Meta description
    meta = clean_text(
        get_meta(soup, name="description")
    )

    if meta:
        return meta

    # Résumé éventuel
    selectors = [
        ".product-info__description",
        ".product__description"
    ]

    for selector in selectors:

        tag = soup.select_one(selector)

        if tag:

            text = clean_html(str(tag))

            if text and len(text) <= 1000:
                return text

    return ""


def get_category(product_json, jsonld, soup):

    # --------------------------------------------------------
    # 1. JSON-LD
    # --------------------------------------------------------

    if isinstance(jsonld, dict):

        category = jsonld.get("category")

        if category:
            category = clean_text(category)

            if category:
                return category, "jsonld"

    # --------------------------------------------------------
    # 2. Shopify type
    # --------------------------------------------------------

    product_type = product_json.get("type")

    if product_type:
        product_type = clean_text(product_type)

        if product_type:
            return product_type, "shopify_type"

    # --------------------------------------------------------
    # 3. Breadcrumb
    # --------------------------------------------------------

    breadcrumb = soup.find(
        attrs={"class": re.compile("breadcrumb", re.I)}
    )

    if breadcrumb:

        links = breadcrumb.find_all("a")

        values = [
            clean_text(a.get_text(" ", strip=True))
            for a in links
        ]

        values = [
            x for x in values
            if x and x.lower() not in (
                "home",
                "startseite"
            )
        ]

        if values:
            return values[-1], "breadcrumb"

    return "", "none"


def classify_product(product_json):

    variants = product_json.get("variants") or []
    options = product_json.get("options") or []

    if len(variants) == 0:
        return "simple"

    if len(variants) > 1:
        return "variable"

    if len(variants) == 1:

        variant = variants[0]

        title = clean_text(
            variant.get("title", "")
        ).lower()

        if title in (
            "",
            "default title"
        ):
            return "simple"

        if options == ["Title"]:
            return "simple"

        return "simple"

    return "simple"


def get_price_data(price, compare_at):

    price_value = money(price)
    compare_value = money(compare_at)

    if (
        price_value != ""
        and compare_value != ""
        and compare_value > price_value
    ):
        return {
            "regular_price": compare_value,
            "sale_price": price_value
        }

    return {
        "regular_price": price_value,
        "sale_price": ""
    }


def extract_variants(product_json):

    result = []

    variants = product_json.get("variants") or []

    for index, variant in enumerate(variants, start=1):

        pricing = get_price_data(
            variant.get("price"),
            variant.get("compare_at_price")
        )

        options = {}

        for n in range(1, 4):

            key = f"option{n}"
            value = variant.get(key)

            if value:
                options[key] = clean_text(value)

        featured_image = ""

        fi = variant.get("featured_image")

        if isinstance(fi, dict):
            featured_image = fi.get("src", "")
        elif isinstance(fi, str):
            featured_image = fi

        item = {
            "position": index,
            "shopify_variant_id": variant.get("id"),
            "title": clean_text(
                variant.get("title", "")
            ),
            "sku": clean_text(
                variant.get("sku", "")
            ),
            "barcode": clean_text(
                variant.get("barcode", "")
            ),
            "available": bool(
                variant.get("available", False)
            ),
            "price": pricing,
            "options": options,
            "requires_shipping": variant.get(
                "requires_shipping"
            ),
            "taxable": variant.get(
                "taxable"
            ),
            "weight": variant.get(
                "weight"
            ),
            "featured_image": normalize_url(
                featured_image
            )
        }

        result.append(item)

    return result


def extract_images(product_json):

    images = []

    raw_images = product_json.get("images") or []

    for image in raw_images:

        if isinstance(image, dict):
            url = (
                image.get("src")
                or image.get("url")
                or image.get("originalSrc")
                or ""
            )
        else:
            url = str(image)

        url = normalize_url(url)

        if url and url not in images:
            images.append(url)

    featured = product_json.get(
        "featured_image"
    )

    featured = normalize_url(featured)

    return {
        "featured_image": featured,
        "images": images
    }


def extract_product(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:
            html = f.read()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        product_json = find_product_json(soup)

        if not product_json:
            return None

        jsonld = get_primary_jsonld(soup)

        title = clean_text(
            product_json.get("title")
            or (
                jsonld.get("name")
                if jsonld else ""
            )
            or soup.title.get_text()
            if soup.title
            else ""
        )

        h1 = soup.find("h1")

        h1_text = (
            clean_text(
                h1.get_text(" ", strip=True)
            )
            if h1
            else ""
        )

        handle = clean_text(
            product_json.get("handle")
        )

        product_id = product_json.get("id")

        vendor = clean_text(
            product_json.get("vendor")
            or "Buture Official"
        )

        product_type = clean_text(
            product_json.get("type")
        )

        tags = product_json.get("tags") or []

        if isinstance(tags, str):
            tags = [clean_text(tags)]

        tags = [
            clean_text(tag)
            for tag in tags
            if clean_text(tag)
        ]

        # ----------------------------------------------------
        # DESCRIPTION
        # ----------------------------------------------------

        description, description_source = find_description(
            soup,
            product_json,
            jsonld
        )

        short_description = find_short_description(
            soup,
            title
        )

        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        category, category_source = get_category(
            product_json,
            jsonld,
            soup
        )

        # ----------------------------------------------------
        # TYPE
        # ----------------------------------------------------

        product_type_wc = classify_product(
            product_json
        )

        # ----------------------------------------------------
        # CURRENCY
        # ----------------------------------------------------

        currency = get_currency(
            soup,
            jsonld
        )

        # ----------------------------------------------------
        # PRICING
        # ----------------------------------------------------

        product_price = product_json.get("price")
        product_compare = product_json.get(
            "compare_at_price"
        )

        pricing = get_price_data(
            product_price,
            product_compare
        )

        # ----------------------------------------------------
        # VARIANTS
        # ----------------------------------------------------

        variants = extract_variants(
            product_json
        )

        # ----------------------------------------------------
        # IMAGES
        # ----------------------------------------------------

        images = extract_images(
            product_json
        )

        # ----------------------------------------------------
        # PRODUCT SKU
        # ----------------------------------------------------

        product_sku = ""

        if len(variants) == 1:
            product_sku = variants[0].get(
                "sku",
                ""
            )

        # ----------------------------------------------------
        # OPTIONS / ATTRIBUTES
        # ----------------------------------------------------

        raw_options = product_json.get(
            "options"
        ) or []

        options = []

        for option in raw_options:

            if isinstance(option, str):
                name = clean_text(option)

            elif isinstance(option, dict):
                name = clean_text(
                    option.get("name", "")
                )

            else:
                name = ""

            if name and name.lower() != "title":
                options.append(name)

        # ----------------------------------------------------
        # AVAILABILITY
        # ----------------------------------------------------

        available = bool(
            product_json.get(
                "available",
                any(
                    v.get("available")
                    for v in variants
                )
            )
        )

        # ----------------------------------------------------
        # PUBLISHED
        # ----------------------------------------------------

        published_at = clean_text(
            product_json.get(
                "published_at"
            )
        )

        # ----------------------------------------------------
        # ANOMALIES
        # ----------------------------------------------------

        anomalies = []

        if not title:
            anomalies.append(
                "missing_title"
            )

        if not description:
            anomalies.append(
                "missing_description"
            )

        if not category:
            anomalies.append(
                "missing_category"
            )

        if not currency:
            anomalies.append(
                "missing_currency"
            )

        if not images["images"]:
            anomalies.append(
                "missing_images"
            )

        if (
            product_type_wc == "variable"
            and not variants
        ):
            anomalies.append(
                "variable_without_variants"
            )

        for variant in variants:

            if variant["price"]["regular_price"] == "":
                anomalies.append(
                    "variant_missing_price"
                )
                break

        return {
            "shopify": {
                "id": product_id,
                "handle": handle,
                "published_at": published_at
            },

            "name": title,

            "slug": handle,

            "h1": h1_text,

            "sku": product_sku,

            "brand": vendor,

            "type": product_type_wc,

            "shopify_type": product_type,

            "category": category,

            "category_source": category_source,

            "tags": tags,

            "description": description,

            "description_source": description_source,

            "short_description": short_description,

            "currency": currency,

            "pricing": pricing,

            "available": available,

            "options": options,

            "variants": variants,

            "images": images["images"],

            "featured_image": images[
                "featured_image"
            ],

            "anomalies": anomalies,

            "source_file": os.path.relpath(
                path,
                "/workspaces/ibuture"
            )
        }

    except Exception as e:

        print(
            f"ERREUR {path}: {e}"
        )

        return None


# ============================================================
# RECHERCHE DES PRODUITS
# ============================================================

def get_product_files():

    if not os.path.isdir(BASE):
        raise RuntimeError(
            f"Dossier introuvable : {BASE}"
        )

    files = []

    for root, dirs, filenames in os.walk(BASE):

        for filename in filenames:

            if filename.lower() != "index.html":
                continue

            path = os.path.join(
                root,
                filename
            )

            files.append(path)

    files.sort()

    return files


# ============================================================
# CSV
# ============================================================

def write_csv(products):

    rows = []

    for p in products:

        variants_count = len(
            p["variants"]
        )

        variant_skus = "; ".join(
            v["sku"]
            for v in p["variants"]
            if v["sku"]
        )

        variant_prices = "; ".join(
            str(
                v["price"]["sale_price"]
                or v["price"]["regular_price"]
            )
            for v in p["variants"]
        )

        image_count = len(
            p["images"]
        )

        rows.append({
            "shopify_id": p["shopify"]["id"],
            "handle": p["shopify"]["handle"],
            "name": p["name"],
            "slug": p["slug"],
            "sku": p["sku"],
            "brand": p["brand"],
            "type": p["type"],
            "shopify_type": p["shopify_type"],
            "category": p["category"],
            "category_source": p["category_source"],
            "description_source": p["description_source"],
            "short_description": p["short_description"],
            "currency": p["currency"],
            "regular_price": p["pricing"]["regular_price"],
            "sale_price": p["pricing"]["sale_price"],
            "available": p["available"],
            "options": " | ".join(
                p["options"]
            ),
            "variants_count": variants_count,
            "variant_skus": variant_skus,
            "variant_prices": variant_prices,
            "images_count": image_count,
            "featured_image": p["featured_image"],
            "tags": " | ".join(
                p["tags"]
            ),
            "description_length": len(
                p["description"]
            ),
            "anomalies": " | ".join(
                p["anomalies"]
            ),
            "source_file": p["source_file"]
        })

    fields = [
        "shopify_id",
        "handle",
        "name",
        "slug",
        "sku",
        "brand",
        "type",
        "shopify_type",
        "category",
        "category_source",
        "description_source",
        "short_description",
        "currency",
        "regular_price",
        "sale_price",
        "available",
        "options",
        "variants_count",
        "variant_skus",
        "variant_prices",
        "images_count",
        "featured_image",
        "tags",
        "description_length",
        "anomalies",
        "source_file"
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("BUTURE — EXTRACTION PRODUITS V6")
    print("=" * 70)

    files = get_product_files()

    print(
        f"Produits trouvés : {len(files)}"
    )

    if LIMIT > 0:
        files = files[:LIMIT]

    print(
        f"Produits à extraire : {len(files)}"
    )

    products = []

    errors = 0

    for index, path in enumerate(
        files,
        start=1
    ):

        product = extract_product(
            path
        )

        if product:

            products.append(
                product
            )

            print(
                f"[{index:04d}] "
                f"{product['slug']} | "
                f"{product['type']} | "
                f"{product['currency']} | "
                f"{len(product['variants'])} var | "
                f"{len(product['images'])} img | "
                f"desc={len(product['description'])} "
                f"[{product['description_source']}]"
            )

        else:

            errors += 1

            print(
                f"[{index:04d}] ERREUR"
            )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    output = {
        "project": "IButure WooCommerce Migration",

        "version": "6",

        "source": "ibuture.com",

        "extraction": {
            "base": BASE,
            "products_found": len(files),
            "products_extracted": len(products),
            "errors": errors
        },

        "products": products
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    write_csv(products)

    # --------------------------------------------------------
    # STATISTIQUES
    # --------------------------------------------------------

    full = sum(
        1
        for p in products
        if p["description_source"] == "full"
    )

    short = sum(
        1
        for p in products
        if p["description_source"] == "short"
    )

    meta = sum(
        1
        for p in products
        if p["description_source"] == "meta_fallback"
    )

    none = sum(
        1
        for p in products
        if p["description_source"] == "none"
    )

    variable = sum(
        1
        for p in products
        if p["type"] == "variable"
    )

    simple = sum(
        1
        for p in products
        if p["type"] == "simple"
    )

    missing_category = sum(
        1
        for p in products
        if not p["category"]
    )

    missing_sku = sum(
        1
        for p in products
        if (
            p["type"] == "simple"
            and not p["sku"]
        )
    )

    anomalous = sum(
        1
        for p in products
        if p["anomalies"]
    )

    currencies = {}

    for p in products:

        currency = p["currency"] or "UNKNOWN"

        currencies[currency] = (
            currencies.get(currency, 0) + 1
        )

    total_variants = sum(
        len(p["variants"])
        for p in products
    )

    total_images = sum(
        len(p["images"])
        for p in products
    )

    print()
    print("=" * 70)
    print("RÉSUMÉ V6")
    print("=" * 70)

    print(
        f"Produits extraits      : {len(products)}"
    )

    print(
        f"Erreurs                : {errors}"
    )

    print(
        f"Descriptions full      : {full}"
    )

    print(
        f"Descriptions short     : {short}"
    )

    print(
        f"Meta fallback          : {meta}"
    )

    print(
        f"Description absente    : {none}"
    )

    print(
        f"Produits variables     : {variable}"
    )

    print(
        f"Produits simples       : {simple}"
    )

    print(
        f"Variantes totales      : {total_variants}"
    )

    print(
        f"Images totales         : {total_images}"
    )

    print(
        f"Catégories absentes    : {missing_category}"
    )

    print(
        f"SKU produit absent     : {missing_sku}"
    )

    print(
        f"Produits avec anomalies: {anomalous}"
    )

    print()
    print("Devises :")

    for currency, count in sorted(
        currencies.items()
    ):
        print(
            f"  {currency}: {count}"
        )

    print()
    print(
        f"JSON : {OUTPUT_JSON}"
    )

    print(
        f"CSV  : {OUTPUT_CSV}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
