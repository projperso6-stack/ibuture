import json
import re
from pathlib import Path
from collections import defaultdict

CATALOG = Path("/workspaces/ibuture/products_catalog_v6.json")
PRODUCTS_DIR = Path("/workspaces/ibuture/site/de/products")

with open(CATALOG, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data.get("products", data)

# ---------------------------------------------------------
# Construire la liste des SKU problématiques
# ---------------------------------------------------------

sku_map = defaultdict(list)

for p in products:
    for v in p.get("variants", []):
        sku = (v.get("sku") or "").strip()

        if sku:
            sku_map[sku].append((p, v))

duplicate_skus = {
    sku: items
    for sku, items in sku_map.items()
    if len(items) > 1
}

print("=" * 90)
print("IBUTURE — AUDIT CATALOGUE V7.3")
print("=" * 90)

print(f"SKU dupliqués analysés : {len(duplicate_skus)}")

# ---------------------------------------------------------
# Recherche d'un SKU dans le HTML du produit
# ---------------------------------------------------------

def find_product_html(slug):

    path = PRODUCTS_DIR / slug / "index.html"

    if not path.exists():
        return None

    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def extract_xcotton(html):

    pattern = re.compile(
        r'<script[^>]+id=["\']xcotton_pp_variants["\'][^>]*>'
        r'(.*?)'
        r'</script>',
        re.I | re.S
    )

    m = pattern.search(html)

    if not m:
        return None

    text = m.group(1).strip()

    try:
        return json.loads(text)
    except Exception:
        return None


def find_variant_in_xcotton(data, variant_id):

    if not data:
        return None

    variants = data.get("variants") or []

    for v in variants:

        vid = (
            v.get("id")
            or v.get("variant_id")
            or v.get("shopify_variant_id")
        )

        if str(vid) == str(variant_id):
            return v

    return None


# ---------------------------------------------------------
# Analyse
# ---------------------------------------------------------

report = []

for sku, items in sorted(duplicate_skus.items()):

    print()
    print("=" * 90)
    print(f"SKU : {sku}")
    print("=" * 90)

    for index, (product, catalog_variant) in enumerate(items, 1):

        slug = product.get("slug")
        variant_id = catalog_variant.get("shopify_variant_id")

        print()
        print(f"[{index}] {slug}")
        print(f"    ID Shopify : {variant_id}")
        print(f"    SKU        : {sku}")

        html = find_product_html(slug)

        if html is None:

            print("    ❌ HTML introuvable")

            report.append({
                "sku": sku,
                "slug": slug,
                "variant_id": variant_id,
                "status": "html_missing"
            })

            continue

        xcotton = extract_xcotton(html)

        if not xcotton:

            print("    ❌ xcotton_pp_variants introuvable")

            report.append({
                "sku": sku,
                "slug": slug,
                "variant_id": variant_id,
                "status": "xcotton_missing"
            })

            continue

        original = find_variant_in_xcotton(
            xcotton,
            variant_id
        )

        if not original:

            print("    ❌ Variante absente de xcotton")

            report.append({
                "sku": sku,
                "slug": slug,
                "variant_id": variant_id,
                "status": "variant_missing"
            })

            continue

        print("    ✅ Variante retrouvée dans Shopify JSON")

        print()
        print("    DONNÉES SHOPIFY ORIGINALES")

        fields = [
            "id",
            "title",
            "sku",
            "barcode",
            "price",
            "compare_at_price",
            "available",
            "featured_image",
            "featured_media",
            "options",
            "weight",
        ]

        for field in fields:

            if field in original:

                value = original.get(field)

                print(f"      {field}: {value}")

        catalog_image = catalog_variant.get("featured_image")
        original_image = original.get("featured_image")

        print()
        print("    CONTRÔLE IMAGE")

        print(f"      Catalogue V6 : {catalog_image}")
        print(f"      Shopify      : {original_image}")

        if original_image and catalog_image:
            if original_image == catalog_image:
                print("      ✅ Image correctement extraite")
            else:
                print("      ⚠️ Image différente")

        elif original_image and not catalog_image:
            print("      🔴 IMAGE PRÉSENTE CHEZ SHOPIFY MAIS ABSENTE DU CATALOGUE")

        elif not original_image:
            print("      ℹ️ Shopify ne fournit pas d'image de variante")

        # Recherche brute du variant ID dans le HTML
        id_found = str(variant_id) in html

        print()
        print(f"    ID présent dans HTML : {'OUI' if id_found else 'NON'}")

        report.append({
            "sku": sku,
            "slug": slug,
            "variant_id": variant_id,
            "status": "ok",
            "shopify_variant": original,
            "catalog_variant": catalog_variant,
            "image_catalog": catalog_image,
            "image_shopify": original_image,
            "variant_id_in_html": id_found
        })


# ---------------------------------------------------------
# Résumé
# ---------------------------------------------------------

print()
print("=" * 90)
print("RÉSUMÉ V7.3")
print("=" * 90)

ok = sum(1 for x in report if x["status"] == "ok")
missing_images = sum(
    1 for x in report
    if x.get("status") == "ok"
    and x.get("image_shopify")
    and not x.get("image_catalog")
)

different_images = sum(
    1 for x in report
    if x.get("status") == "ok"
    and x.get("image_shopify")
    and x.get("image_catalog")
    and x.get("image_shopify") != x.get("image_catalog")
)

print(f"Variantes analysées : {len(report)}")
print(f"Variantes retrouvées : {ok}")
print(f"Images absentes du catalogue mais présentes Shopify : {missing_images}")
print(f"Images différentes : {different_images}")

print()
print("STATUT")

if missing_images == 0:
    print("✅ Aucune image de variante réellement perdue.")
else:
    print("⚠️ Certaines images de variantes doivent être récupérées.")

OUTPUT = "/workspaces/ibuture/audit_v7_3.json"

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print()
print(f"Rapport JSON : {OUTPUT}")
print()
print("=" * 90)
print("FIN V7.3")
print("=" * 90)
