import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

SITE = Path("site")
OUTPUT = Path("products_sample_v2.json")
LIMIT = 20


def clean_url(url):
    if not url:
        return None

    url = str(url).replace("\\/", "/")

    if url.startswith("//"):
        url = "https:" + url

    return url


def clean_text(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def get_json_ld(soup):
    result = []

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        text = script.get_text(strip=True)

        if not text:
            continue

        try:
            data = json.loads(text)

            if isinstance(data, list):
                result.extend(data)
            else:
                result.append(data)

        except Exception:
            continue

    return result


def extract_category(json_ld):
    for item in json_ld:

        if not isinstance(item, dict):
            continue

        if item.get("@type") in (
            "Product",
            "ProductGroup"
        ):

            category = item.get("category")

            if category:
                return category

    return None


def extract_faq(json_ld):

    faq = []

    for item in json_ld:

        if not isinstance(item, dict):
            continue

        if item.get("@type") != "FAQPage":
            continue

        for question in item.get("mainEntity", []):

            if not isinstance(question, dict):
                continue

            name = question.get("name")

            answer = question.get(
                "acceptedAnswer",
                {}
            )

            if not isinstance(answer, dict):
                answer = {}

            text = answer.get("text")

            if name and text:

                faq.append({
                    "question": clean_text(name),
                    "answer_html": text,
                    "answer_text": clean_text(
                        BeautifulSoup(
                            text,
                            "html.parser"
                        ).get_text(" ", strip=True)
                    )
                })

    return faq


def extract_description(soup):

    blocks = soup.select(
        ".product-info__description"
    )

    if not blocks:
        return {
            "html": "",
            "text": ""
        }

    # Plusieurs blocs peuvent être des duplications
    # responsive/mobile. On prend le plus riche.
    best = max(
        blocks,
        key=lambda x: len(str(x))
    )

    html = best.decode_contents()

    text = best.get_text(
        " ",
        strip=True
    )

    return {
        "html": html.strip(),
        "text": clean_text(text)
    }


def extract_product(path):

    html = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # -------------------------------------------------
    # SHOPIFY PRODUCT JSON
    # -------------------------------------------------

    script = soup.find(
        "script",
        id="xcotton_pp_variants"
    )

    if not script:
        return None

    try:
        data = json.loads(
            script.get_text(strip=True)
        )
    except Exception as e:
        print(
            "JSON ERROR:",
            path,
            e
        )
        return None

    # -------------------------------------------------
    # JSON-LD
    # -------------------------------------------------

    json_ld = get_json_ld(soup)

    category = extract_category(
        json_ld
    )

    faq = extract_faq(
        json_ld
    )

    # -------------------------------------------------
    # DESCRIPTION
    # -------------------------------------------------

    description = extract_description(
        soup
    )

    # -------------------------------------------------
    # META DESCRIPTION
    # -------------------------------------------------

    meta_description = ""

    meta = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta:
        meta_description = (
            meta.get("content") or ""
        )

    # -------------------------------------------------
    # CURRENCY
    # -------------------------------------------------

    currency = None

    # 1. Meta Shopify
    currency_meta = soup.find(
        "meta",
        attrs={
            "property":
            "product:price:currency"
        }
    )

    if currency_meta:
        currency = currency_meta.get(
            "content"
        )

    # 2. storefrontCurrency
    if not currency:

        match = re.search(
            r"storefrontCurrency\s*[:=]\s*['\"]([^'\"]+)",
            html,
            re.I
        )

        if match:
            currency = match.group(1)

    # -------------------------------------------------
    # IMAGES
    # -------------------------------------------------

    images = []

    for image in data.get(
        "images",
        []
    ):

        url = clean_url(image)

        if url and url not in images:
            images.append(url)

    # -------------------------------------------------
    # MEDIA
    # -------------------------------------------------

    media = []

    for item in data.get(
        "media",
        []
    ):

        if not isinstance(item, dict):
            continue

        media.append({
            "id": item.get("id"),
            "position": item.get("position"),
            "media_type": item.get("media_type"),
            "alt": item.get("alt"),
            "width": item.get("width"),
            "height": item.get("height"),
            "aspect_ratio": item.get(
                "aspect_ratio"
            ),
            "src": clean_url(
                item.get("src")
            )
        })

    # -------------------------------------------------
    # VARIANTS
    # -------------------------------------------------

    variants = []

    for variant in data.get(
        "variants",
        []
    ):

        if not isinstance(
            variant,
            dict
        ):
            continue

        featured = (
            variant.get(
                "featured_image"
            ) or {}
        )

        variants.append({

            "shopify_id":
                variant.get("id"),

            "title":
                variant.get("title"),

            "name":
                variant.get("name"),

            "public_title":
                variant.get(
                    "public_title"
                ),

            "sku":
                variant.get("sku"),

            "price_cents":
                variant.get("price"),

            "compare_at_price_cents":
                variant.get(
                    "compare_at_price"
                ),

            "available":
                variant.get(
                    "available"
                ),

            "inventory_management":
                variant.get(
                    "inventory_management"
                ),

            "inventory_quantity":
                variant.get(
                    "inventory_quantity"
                ),

            "weight":
                variant.get("weight"),

            "requires_shipping":
                variant.get(
                    "requires_shipping"
                ),

            "taxable":
                variant.get(
                    "taxable"
                ),

            "options":
                variant.get(
                    "options"
                ) or [],

            "option1":
                variant.get("option1"),

            "option2":
                variant.get("option2"),

            "option3":
                variant.get("option3"),

            "featured_image":
                {
                    "id":
                        featured.get("id"),

                    "position":
                        featured.get(
                            "position"
                        ),

                    "alt":
                        featured.get("alt"),

                    "width":
                        featured.get(
                            "width"
                        ),

                    "height":
                        featured.get(
                            "height"
                        ),

                    "src":
                        clean_url(
                            featured.get(
                                "src"
                            )
                        )
                }
                if featured
                else None
        })

    # -------------------------------------------------
    # PRODUCT TYPE
    # -------------------------------------------------

    product_type = (
        data.get("type")
        or ""
    )

    # -------------------------------------------------
    # SIMPLE / VARIABLE
    # -------------------------------------------------

    is_variable = (
        len(variants) > 1
        or len(
            data.get(
                "options"
            ) or []
        ) > 0
    )

    # -------------------------------------------------
    # FINAL PRODUCT
    # -------------------------------------------------

    product = {

        "source_file":
            str(path),

        "shopify_id":
            data.get("id"),

        "title":
            data.get("title"),

        "slug":
            data.get("handle"),

        "description_html":
            description["html"],

        "description_text":
            description["text"],

        "meta_description":
            meta_description,

        "vendor":
            data.get("vendor"),

        "type":
            product_type,

        "category":
            category,

        "tags":
            data.get("tags") or [],

        "currency":
            currency,

        "price_cents":
            data.get("price"),

        "price_min_cents":
            data.get("price_min"),

        "price_max_cents":
            data.get("price_max"),

        "compare_at_price_cents":
            data.get(
                "compare_at_price"
            ),

        "compare_at_price_min_cents":
            data.get(
                "compare_at_price_min"
            ),

        "compare_at_price_max_cents":
            data.get(
                "compare_at_price_max"
            ),

        "available":
            data.get("available"),

        "price_varies":
            data.get(
                "price_varies"
            ),

        "product_type_wc":
            "variable"
            if is_variable
            else "simple",

        "options":
            data.get("options") or [],

        "featured_image":
            clean_url(
                data.get(
                    "featured_image"
                )
            ),

        "images":
            images,

        "media":
            media,

        "variants":
            variants,

        "faq":
            faq
    }

    return product


# =====================================================
# EXTRACTION
# =====================================================

files = sorted(
    SITE.glob(
        "*/products/*/index.html"
    )
)

print(
    "Produits trouvés :",
    len(files)
)

print(
    "Extraction de",
    min(LIMIT, len(files)),
    "produits...\n"
)

products = []

for path in files:

    if len(products) >= LIMIT:
        break

    print(
        "→",
        path
    )

    product = extract_product(
        path
    )

    if product:
        products.append(
            product
        )


OUTPUT.write_text(
    json.dumps(
        products,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


# =====================================================
# RAPPORT
# =====================================================

print()
print("=" * 70)
print("EXTRACTION V2 TERMINÉE")
print("=" * 70)

print(
    "Produits :",
    len(products)
)

print(
    "Fichier :",
    OUTPUT
)

print()

for p in products:

    print(
        f"{p['title']}"
    )

    print(
        f"  type       : {p['product_type_wc']}"
    )

    print(
        f"  catégorie  : {p['category']}"
    )

    print(
        f"  devise     : {p['currency']}"
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
