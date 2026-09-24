import json
from collections import defaultdict

INPUT = "/workspaces/ibuture/products_catalog_v6.json"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data.get("products", data)

print("=" * 80)
print("IBUTURE — AUDIT CATALOGUE V7.2")
print("=" * 80)

# ---------------------------------------------------------
# 1. Index des SKU variantes
# ---------------------------------------------------------

sku_map = defaultdict(list)

for p in products:
    slug = p.get("slug") or p.get("handle") or "UNKNOWN"
    title = p.get("name") or p.get("title") or slug

    for v in p.get("variants") or []:
        sku = (v.get("sku") or "").strip()

        if sku:
            sku_map[sku].append({
                "product": slug,
                "product_title": title,
                "variant": v
            })


duplicates = {
    sku: items
    for sku, items in sku_map.items()
    if len(items) > 1
}


# ---------------------------------------------------------
# 2. Fonction comparaison
# ---------------------------------------------------------

def compare_variants(a, b):

    va = a["variant"]
    vb = b["variant"]

    fields = [
        "title",
        "barcode",
        "price",
        "options",
        "requires_shipping",
        "taxable",
        "weight",
        "featured_image",
        "available",
    ]

    differences = []

    for field in fields:

        value_a = va.get(field)
        value_b = vb.get(field)

        if value_a != value_b:
            differences.append({
                "field": field,
                "a": value_a,
                "b": value_b
            })

    return differences


# ---------------------------------------------------------
# 3. Analyse des doublons
# ---------------------------------------------------------

print()
print("-" * 80)
print("ANALYSE DES SKU DUPLIQUÉS")
print("-" * 80)

identical_count = 0
different_count = 0

duplicate_report = []

for sku, items in sorted(duplicates.items()):

    print()
    print("=" * 80)
    print(f"SKU : {sku}")
    print("=" * 80)

    # Normalement 2 occurrences
    for i, item in enumerate(items, 1):

        v = item["variant"]

        print()
        print(f"[{i}] PRODUIT")
        print(f"    slug       : {item['product']}")
        print(f"    titre      : {item['product_title']}")
        print(f"    variante   : {v.get('title')}")
        print(f"    ID Shopify : {v.get('shopify_variant_id')}")
        print(f"    SKU        : {v.get('sku')}")
        print(f"    prix       : {v.get('price')}")
        print(f"    options    : {v.get('options')}")
        print(f"    disponible : {v.get('available')}")
        print(f"    poids      : {v.get('weight')}")
        print(f"    barcode    : {v.get('barcode')}")
        print(f"    image      : {v.get('featured_image')}")

    # Comparaison paire à paire
    if len(items) == 2:

        differences = compare_variants(items[0], items[1])

        print()
        print("COMPARAISON")

        if not differences:
            print("    ✅ DONNÉES IDENTIQUES")
            identical_count += 1
            classification = "IDENTIQUE"
        else:
            print("    ⚠️ DONNÉES DIFFÉRENTES")
            different_count += 1
            classification = "DIFFERENT"

            for diff in differences:
                print()
                print(f"    Champ : {diff['field']}")
                print(f"      A : {diff['a']}")
                print(f"      B : {diff['b']}")

        duplicate_report.append({
            "sku": sku,
            "classification": classification,
            "products": [
                items[0]["product"],
                items[1]["product"]
            ],
            "ids": [
                items[0]["variant"].get("shopify_variant_id"),
                items[1]["variant"].get("shopify_variant_id")
            ],
            "differences": differences
        })


# ---------------------------------------------------------
# 4. Variantes sans SKU
# ---------------------------------------------------------

print()
print("-" * 80)
print("VARIANTES SANS SKU")
print("-" * 80)

missing_sku = []

for p in products:

    slug = p.get("slug") or p.get("handle") or "UNKNOWN"

    for v in p.get("variants") or []:

        if not (v.get("sku") or "").strip():

            missing_sku.append({
                "product": slug,
                "title": p.get("name") or p.get("title"),
                "variant": v.get("title"),
                "id": v.get("shopify_variant_id"),
                "price": v.get("price"),
                "available": v.get("available")
            })

for item in missing_sku:

    print()
    print(f"Produit   : {item['product']}")
    print(f"Titre     : {item['title']}")
    print(f"Variante  : {item['variant']}")
    print(f"ID        : {item['id']}")
    print(f"Prix      : {item['price']}")
    print(f"Disponible: {item['available']}")


# ---------------------------------------------------------
# 5. Résumé
# ---------------------------------------------------------

print()
print("=" * 80)
print("RÉSUMÉ V7.2")
print("=" * 80)

print(f"Produits                  : {len(products)}")
print(f"SKU dupliqués             : {len(duplicates)}")
print(f"Doublons identiques       : {identical_count}")
print(f"Doublons différents       : {different_count}")
print(f"Variantes sans SKU        : {len(missing_sku)}")

print()
print("INTERPRÉTATION")

if different_count == 0:
    print("✅ Tous les SKU dupliqués ont des données identiques.")
    print("   Ils semblent correspondre à des bundles identiques.")
else:
    print("⚠️ Certains SKU dupliqués ont des données différentes.")
    print("   Ils doivent être traités individuellement avant WooCommerce.")

if missing_sku:
    print("⚠️ Une ou plusieurs variantes n'ont pas de SKU.")
else:
    print("✅ Toutes les variantes possèdent un SKU.")

# ---------------------------------------------------------
# 6. Rapport JSON
# ---------------------------------------------------------

OUTPUT = "/workspaces/ibuture/audit_v7_2.json"

report = {
    "products": len(products),
    "duplicate_skus": len(duplicates),
    "identical_duplicates": identical_count,
    "different_duplicates": different_count,
    "missing_sku_variants": missing_sku,
    "duplicates": duplicate_report
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print()
print(f"Rapport JSON : {OUTPUT}")

print()
print("=" * 80)
print("FIN V7.2")
print("=" * 80)
