import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

SITE = Path("site/de/products")
OUTPUT = Path("products_sample_v3.json")
LIMIT = 50


# ============================================================
# UTILITAIRES
# ============================================================

def clean_url(url):
    if not url:
        return None

    url = str(url).replace("\\/", "/").strip()

    if url.startswith("//"):
        return "https:" + url

    return url


def money(value):
    if value is None or value == "":
        return None

    try:
        return round(float(value) / 100, 2)
    except:
        try:
            return round(float(value), 2)
        except:
            return None


def normalize_text(value):
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


# ============================================================
# JSON
# ============================================================

def parse_json_script(script):
    try:
        return json.loads(script.string or script.get_text())
    except:
        return None


def get_product_json(soup):
    script = soup.find("script", id="xcotton_pp_variants")

    if not script:
        return None

    return parse_json_script(script)


def get_json_ld(soup):
    results = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    ):
        try:
            data = json.loads(script.string or script.get_text())

            if isinstance(data, list):
                results.extend(data)

            else:
                results.append(data)

        except:
            continue

    return results


def find_jsonld_product(jsonlds):

    def recursive_find(obj):

        if isinstance(obj, dict):

            obj_type = obj.get("@type")

            if obj_type in ("Product", "ProductGroup"):
                return obj

            graph = obj.get("@graph")

            if isinstance(graph, list):
                for item in graph:
                    found = recursive_find(item)

                    if found:
                        return found

        elif isinstance(obj, list):

            for item in obj:
                found = recursive_find(item)

                if found:
                    return found

        return None

    return recursive_find(jsonlds)


# ============================================================
# DEVISE SHOPIFY
# ============================================================

def get_shopify_currency(soup):

    # 1. storefrontCurrency dans les scripts
    text = str(soup)

    patterns = [
        r"storefrontCurrency\s*[:=]\s*['\"]([A-Z]{3})['\"]",
        r'"storefrontCurrency"\s*:\s*"([A-Z]{3})"',
        r"'storefrontCurrency'\s*:\s*'([A-Z]{3})'",
    ]

    for pattern in patterns:

        match = re.search(pattern, text, re.I)

        if match:
            return match.group(1).upper()

    # 2. meta Shopify
    metas = [
        ("property", "product:price:currency"),
        ("name", "product:price:currency"),
    ]

    for attr, value in metas:

        tag = soup.find("meta", attrs={attr: value})

        if tag and tag.get("content"):

            currency = tag["content"].strip().upper()

            if re.fullmatch(r"[A-Z]{3}", currency):
                return currency

    # 3. fallback
    return None


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(soup, product_json, jsonld_product):

    candidates = []

    # --------------------------------------------------------
    # 1. Bloc principal Shopify
    # --------------------------------------------------------

    selectors = [
        ".product-info__description",
        "[class*='product-info__description']",
        ".product__description",
        "[class*='product-description']",
        "[class*='product__description']",
        ".description",
    ]

    for selector in selectors:

        for node in soup.select(selector):

            html = node.decode_contents().strip()

            text = normalize_text(
                BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
            )

            if len(text) >= 20:
                candidates.append((len(text), html))

    # --------------------------------------------------------
    # 2. description Shopify JSON
    # --------------------------------------------------------

    if product_json:

        description = product_json.get("description")

        if description:

            html = str(description).strip()

            text = normalize_text(
                BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
            )

            if len(text) >= 20:
                candidates.append((len(text), html))

    # --------------------------------------------------------
    # 3. JSON-LD
    # --------------------------------------------------------

    if jsonld_product:

        description = jsonld_product.get("description")

        if description:

            html = str(description).strip()

            text = normalize_text(
                BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
            )

            if len(text) >= 20:
                candidates.append((len(text), html))

    # --------------------------------------------------------
    # meilleur candidat
    # --------------------------------------------------------

    if not candidates:
        return ""

    candidates.sort(key=lambda x: x[0], reverse=True)

    return candidates[0][1]


# ============================================================
# META DESCRIPTION
# ============================================================

def extract_meta_description(soup):

    tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if tag:
        return tag.get("content", "").strip()

    return ""


# ============================================================
# FAQ
# ============================================================

def extract_faq(jsonlds):

    faqs = []

    def scan(obj):

        if isinstance(obj, dict):

            if obj.get("@type") == "FAQPage":

                main = obj.get("mainEntity", [])

                for item in main:

                    if not isinstance(item, dict):
                        continue

                    question = item.get("name", "")

                    answer = item.get("acceptedAnswer", {})

                    if isinstance(answer, dict):
                        answer = answer.get("text", "")

                    if question and answer:

                        faqs.append({
                            "question": normalize_text(question),
                            "answer_html": str(answer).strip()
                        })

            for value in obj.values():
                scan(value)

        elif isinstance(obj, list):

            for item in obj:
                scan(item)

    scan(jsonlds)

    return faqs


# ============================================================
# IMAGES / MEDIA
# ============================================================

def extract_images(product_json):

    images = []

    if not product_json:
        return images

    for image in product_json.get("images", []):

        url = clean_url(image)

        if url and url not in images:
            images.append(url)

    return images


def extract_media(product_json):

    media = []

    if not product_json:
        return media

    for item in product_json.get("media", []):

        if not isinstance(item, dict):
            continue

        entry = {
            "type": item.get("media_type") or item.get("type"),
            "id": item.get("id"),
            "src": clean_url(
                item.get("src")
                or item.get("preview_image", {}).get("src")
                if isinstance(item.get("preview_image"), dict)
                else None
            ),
        }

        media.append(entry)

    return media


# ============================================================
# TYPE SIMPLE / VARIABLE
# ============================================================

def is_variable(product_json):

    variants = product_json.get("variants", []) if product_json else []
    options = product_json.get("options", []) if product_json else []

    # Plusieurs variantes = variable
    if len(variants) > 1:
        return True

    # Pas de variante
    if len(variants) == 0:
        return False

    variant = variants[0]

    option_values = [
        variant.get("option1"),
        variant.get("option2"),
        variant.get("option3"),
    ]

    option_values = [
        str(v).strip()
        for v in option_values
        if v not in (None, "")
    ]

    # Shopify utilise souvent "Title" pour les produits simples
    if (
        len(options) == 1
        and str(options[0]).strip().lower() == "title"
    ):
        return False

    # Default Title = produit simple
    if (
        variant.get("title")
        and str(variant.get("title")).strip().lower()
        == "default title"
    ):
        return False

    # Une seule variante avec une vraie option
    # peut rester simple si l'option est uniquement descriptive.
    return False


# ============================================================
# VARIANTES
# ============================================================

def extract_variants(product_json):

    variants = []

    if not product_json:
        return variants

    for variant in product_json.get("variants", []):

        if not isinstance(variant, dict):
            continue

        price = money(variant.get("price"))
        compare = money(variant.get("compare_at_price"))

        # WooCommerce :
        # regular_price = ancien prix
        # sale_price = prix actuel

        if (
            compare is not None
            and price is not None
            and compare > price
        ):
            regular_price = compare
            sale_price = price

        else:
            regular_price = price
            sale_price = None

        variants.append({
            "shopify_id": variant.get("id"),
            "sku": variant.get("sku"),
            "title": variant.get("title"),
            "option1": variant.get("option1"),
            "option2": variant.get("option2"),
            "option3": variant.get("option3"),
            "public_title": variant.get("public_title"),
            "name": variant.get("name"),
            "price": price,
            "compare_at_price": compare,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "available": variant.get("available"),
            "requires_shipping": variant.get("requires_shipping"),
            "taxable": variant.get("taxable"),
            "weight": variant.get("weight"),
            "barcode": variant.get("barcode"),
            "inventory_management": variant.get("inventory_management"),
            "featured_image": clean_url(
                variant.get("featured_image")
            ),
        })

    return variants


# ============================================================
# PRODUIT
# ============================================================

def extract_product(path):

    html = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    soup = BeautifulSoup(html, "html.parser")

    product_json = get_product_json(soup)

    if not product_json:
        return None

    jsonlds = get_json_ld(soup)

    jsonld_product = find_jsonld_product(jsonlds)

    # --------------------------------------------------------
    # identité
    # --------------------------------------------------------

    title = product_json.get("title")

    if not title:

        h1 = soup.find("h1")

        if h1:
            title = normalize_text(h1.get_text(" ", strip=True))

    handle = product_json.get("handle")

    # --------------------------------------------------------
    # prix
    # --------------------------------------------------------

    price = money(product_json.get("price"))
    price_min = money(product_json.get("price_min"))
    price_max = money(product_json.get("price_max"))

    compare = money(product_json.get("compare_at_price"))

    # --------------------------------------------------------
    # prix WooCommerce
    # --------------------------------------------------------

    if (
        compare is not None
        and price is not None
        and compare > price
    ):
        regular_price = compare
        sale_price = price

    else:
        regular_price = price
        sale_price = None

    # --------------------------------------------------------
    # catégorie
    # --------------------------------------------------------

    category = None

    if jsonld_product:
        category = jsonld_product.get("category")

    if not category:
        category = product_json.get("type")

    # --------------------------------------------------------
    # options
    # --------------------------------------------------------

    options = product_json.get("options", [])

    # --------------------------------------------------------
    # variantes
    # --------------------------------------------------------

    variants = extract_variants(product_json)

    # --------------------------------------------------------
    # images
    # --------------------------------------------------------

    images = extract_images(product_json)

    media = extract_media(product_json)

    # --------------------------------------------------------
    # description
    # --------------------------------------------------------

    description_html = extract_description(
        soup,
        product_json,
        jsonld_product
    )

    description_text = normalize_text(
        BeautifulSoup(
            description_html,
            "html.parser"
        ).get_text(" ", strip=True)
    )

    # --------------------------------------------------------
    # FAQ
    # --------------------------------------------------------

    faq = extract_faq(jsonlds)

    # --------------------------------------------------------
    # type
    # --------------------------------------------------------

    product_type = (
        "variable"
        if is_variable(product_json)
        else "simple"
    )

    # --------------------------------------------------------
    # disponibilité
    # --------------------------------------------------------

    available = product_json.get("available")

    # --------------------------------------------------------
    # résultat
    # --------------------------------------------------------

    return {
        "source_file": str(path),
        "shopify_id": product_json.get("id"),
        "handle": handle,
        "title": title,
        "vendor": product_json.get("vendor"),
        "shopify_type": product_json.get("type"),
        "tags": product_json.get("tags") or [],
        "category": category,
        "product_type": product_type,

        "currency": get_shopify_currency(soup),

        "price": price,
        "price_min": price_min,
        "price_max": price_max,
        "compare_at_price": compare,
        "regular_price": regular_price,
        "sale_price": sale_price,

        "available": available,

        "options": options,
        "variants": variants,

        "images": images,
        "media": media,

        "description_html": description_html,
        "description_text": description_text,

        "meta_description": extract_meta_description(soup),

        "faq": faq,

        "jsonld_type": (
            jsonld_product.get("@type")
            if jsonld_product
            else None
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    files = sorted(
        SITE.glob("*/index.html")
    )

    print(f"Produits trouvés : {len(files)}")

    selected = files[:LIMIT]

    print(f"Extraction de {len(selected)} produits...\n")

    products = []

    errors = []

    for path in selected:

        print(f"→ {path}")

        try:

            product = extract_product(path)

            if product:
                products.append(product)

            else:
                errors.append(
                    f"{path} : données Shopify introuvables"
                )

        except Exception as e:

            errors.append(
                f"{path} : {type(e).__name__}: {e}"
            )

    OUTPUT.write_text(
        json.dumps(
            products,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print("=" * 70)
    print("EXTRACTION V3 TERMINÉE")
    print("=" * 70)

    print(f"Produits : {len(products)}")
    print(f"Erreurs  : {len(errors)}")
    print(f"Fichier  : {OUTPUT}")

    print()

    for p in products:

        print(p["title"])

        print(
            f"  type       : {p['product_type']}"
        )

        print(
            f"  catégorie  : {p['category']}"
        )

        print(
            f"  devise     : {p['currency']}"
        )

        print(
            f"  prix       : {p['price']}"
        )

        print(
            f"  variantes  : {len(p['variants'])}"
        )

        print(
            f"  images     : {len(p['images'])}"
        )

        print(
            f"  médias     : {len(p['media'])}"
        )

        print(
            f"  FAQ        : {len(p['faq'])}"
        )

        print(
            f"  desc HTML  : {len(p['description_html'])} caractères"
        )

        print()

    if errors:

        print("ERREURS :")

        for error in errors:
            print(" -", error)


if __name__ == "__main__":
    main()

