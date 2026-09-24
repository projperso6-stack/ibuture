import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

SITE = Path("site")
OUTPUT = Path("products_sample.json")
LIMIT = 10


def clean_url(url):
    if not url:
        return None

    url = url.replace("\\/", "/")

    if url.startswith("//"):
        url = "https:" + url

    return url


def extract_product_from_html(path):

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # --------------------------------------------------
    # Bloc principal xcotton_pp_variants
    # --------------------------------------------------

    script = soup.find("script", id="xcotton_pp_variants")

    if not script:
        return None

    text = script.get_text(strip=True)

    try:
        data = json.loads(text)
    except Exception as e:
        print("JSON ERROR:", path, e)
        return None

    # --------------------------------------------------
    # Produit
    # --------------------------------------------------

    product = {
        "source_file": str(path),
        "shopify_id": data.get("id"),
        "title": data.get("title"),
        "slug": data.get("handle"),
        "description": data.get("description"),
        "vendor": data.get("vendor"),
        "type": data.get("type"),
        "tags": data.get("tags") or [],
        "price_cents": data.get("price"),
        "price_min_cents": data.get("price_min"),
        "price_max_cents": data.get("price_max"),
        "compare_at_price_cents": data.get("compare_at_price"),
        "compare_at_price_min_cents": data.get("compare_at_price_min"),
        "compare_at_price_max_cents": data.get("compare_at_price_max"),
        "available": data.get("available"),
        "price_varies": data.get("price_varies"),
        "currency": None,
        "options": data.get("options") or [],
        "featured_image": clean_url(data.get("featured_image")),
        "images": [],
        "media": [],
        "variants": []
    }

    # --------------------------------------------------
    # Devise
    # --------------------------------------------------

    currency = soup.find(
        "meta",
        attrs={"property": "product:price:currency"}
    )

    if currency:
        product["currency"] = currency.get("content")

    # --------------------------------------------------
    # Images
    # --------------------------------------------------

    for image in data.get("images") or []:

        url = clean_url(image)

        if url and url not in product["images"]:
            product["images"].append(url)

    # --------------------------------------------------
    # Media
    # --------------------------------------------------

    for media in data.get("media") or []:

        if not isinstance(media, dict):
            continue

        item = {
            "id": media.get("id"),
            "position": media.get("position"),
            "media_type": media.get("media_type"),
            "alt": media.get("alt"),
            "width": media.get("width"),
            "height": media.get("height"),
            "aspect_ratio": media.get("aspect_ratio"),
            "src": clean_url(media.get("src"))
        }

        product["media"].append(item)

    # --------------------------------------------------
    # Variantes
    # --------------------------------------------------

    for variant in data.get("variants") or []:

        if not isinstance(variant, dict):
            continue

        featured = variant.get("featured_image") or {}
        featured_media = variant.get("featured_media") or {}

        variant_data = {
            "shopify_id": variant.get("id"),
            "title": variant.get("title"),
            "name": variant.get("name"),
            "public_title": variant.get("public_title"),
            "sku": variant.get("sku"),
            "price_cents": variant.get("price"),
            "compare_at_price_cents": variant.get("compare_at_price"),
            "available": variant.get("available"),
            "inventory_management": variant.get("inventory_management"),
            "inventory_quantity": variant.get("inventory_quantity"),
            "weight": variant.get("weight"),
            "requires_shipping": variant.get("requires_shipping"),
            "taxable": variant.get("taxable"),
            "options": variant.get("options") or [],
            "option1": variant.get("option1"),
            "option2": variant.get("option2"),
            "option3": variant.get("option3"),
            "featured_image": {
                "id": featured.get("id"),
                "position": featured.get("position"),
                "alt": featured.get("alt"),
                "width": featured.get("width"),
                "height": featured.get("height"),
                "src": clean_url(featured.get("src"))
            } if featured else None,
            "featured_media": {
                "id": featured_media.get("id"),
                "position": featured_media.get("position"),
                "alt": featured_media.get("alt"),
                "width": featured_media.get("width"),
                "height": featured_media.get("height"),
                "src": clean_url(
                    featured_media.get("preview_image", {}).get("src")
                    if isinstance(featured_media.get("preview_image"), dict)
                    else None
                )
            } if featured_media else None
        }

        product["variants"].append(variant_data)

    return product


# ======================================================
# Sélection des produits
# ======================================================

files = sorted(SITE.glob("*/products/*/index.html"))

print("Produits trouvés :", len(files))
print("Extraction de", min(LIMIT, len(files)), "produits...\n")

products = []

for path in files:

    if len(products) >= LIMIT:
        break

    print("→", path)

    product = extract_product_from_html(path)

    if product:
        products.append(product)


# ======================================================
# Sauvegarde
# ======================================================

OUTPUT.write_text(
    json.dumps(
        products,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print("\n==========================================")
print("EXTRACTION TERMINÉE")
print("==========================================")
print("Produits :", len(products))
print("Fichier  :", OUTPUT)
print()

for p in products:

    print(
        f"{p['title']} | "
        f"variantes={len(p['variants'])} | "
        f"images={len(p['images'])} | "
        f"options={p['options']}"
    )
