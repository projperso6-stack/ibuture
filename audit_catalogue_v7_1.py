import json
from collections import defaultdict

INPUT = "/workspaces/ibuture/products_catalog_v6.json"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data.get("products", data)

print("=" * 70)
print("IBUTURE — AUDIT CATALOGUE V7.1")
print("=" * 70)

print(f"Produits : {len(products)}")

# ---------------------------------------------------------
# Afficher la structure réelle d'une variante
# ---------------------------------------------------------

first_variant = None

for p in products:
    variants = p.get("variants") or []
    if variants:
        first_variant = variants[0]
        break

print()
print("-" * 70)
print("STRUCTURE RÉELLE D'UNE VARIANTE")
print("-" * 70)

if first_variant:
    for key, value in first_variant.items():
        print(f"{key}: {value}")
else:
    print("Aucune variante trouvée.")

# ---------------------------------------------------------
# SKU variantes
# ---------------------------------------------------------

sku_locations = defaultdict(list)

for p in products:

    slug = p.get("slug") or p.get("handle") or "UNKNOWN"
    title = p.get("name") or p.get("title") or slug

    for v in p.get("variants") or []:

        sku = (
            v.get("sku")
            or v.get("SKU")
            or ""
        ).strip()

        variant_title = (
            v.get("title")
            or v.get("name")
            or ""
        )

        variant_id = (
            v.get("id")
            or v.get("variant_id")
            or v.get("shopify_id")
            or v.get("shopify_variant_id")
        )

        if sku:
            sku_locations[sku].append({
                "product": slug,
                "title": title,
                "variant": variant_title,
                "variant_id": variant_id
            })

# ---------------------------------------------------------
# Doublons SKU
# ---------------------------------------------------------

duplicates = {
    sku: locations
    for sku, locations in sku_locations.items()
    if len(locations) > 1
}

print()
print("-" * 70)
print("SKU VARIANTES DUPLIQUÉS")
print("-" * 70)

print(f"Nombre de SKU dupliqués : {len(duplicates)}")

for sku, locations in sorted(duplicates.items()):

    print()
    print(f"SKU : {sku}")

    for loc in locations:
        print(
            f"  → {loc['product']} | "
            f"{loc['variant']} | "
            f"ID={loc['variant_id']}"
        )

# ---------------------------------------------------------
# Variantes sans SKU
# ---------------------------------------------------------

missing = []

for p in products:

    slug = p.get("slug") or p.get("handle") or "UNKNOWN"

    for v in p.get("variants") or []:

        sku = (
            v.get("sku")
            or v.get("SKU")
            or ""
        ).strip()

        if not sku:
            missing.append({
                "product": slug,
                "variant": v.get("title") or v.get("name") or "",
                "id": (
                    v.get("id")
                    or v.get("variant_id")
                    or v.get("shopify_id")
                    or v.get("shopify_variant_id")
                )
            })

print()
print("-" * 70)
print("VARIANTES SANS SKU")
print("-" * 70)

print(f"Total : {len(missing)}")

for item in missing:
    print(
        f" - {item['product']} → "
        f"{item['variant']} | ID={item['id']}"
    )

# ---------------------------------------------------------
# IDs variantes
# ---------------------------------------------------------

variant_ids = []

for p in products:

    slug = p.get("slug") or p.get("handle") or "UNKNOWN"

    for v in p.get("variants") or []:

        vid = (
            v.get("id")
            or v.get("variant_id")
            or v.get("shopify_id")
            or v.get("shopify_variant_id")
        )

        if vid is not None:
            variant_ids.append(str(vid))

print()
print("-" * 70)
print("IDS VARIANTES")
print("-" * 70)

print(f"Variantes avec ID : {len(variant_ids)}")

if variant_ids:
    print(f"Premier ID : {variant_ids[0]}")

print(f"IDs uniques       : {len(set(variant_ids))}")

print()
print("=" * 70)
print("FIN V7.1")
print("=" * 70)
