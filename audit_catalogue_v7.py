import json
from collections import Counter

INPUT = "/workspaces/ibuture/products_catalog_v6.json"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data.get("products", data)

if not isinstance(products, list):
    raise ValueError("Format JSON inattendu : liste de produits introuvable.")

print("=" * 70)
print("IBUTURE — AUDIT CATALOGUE V7")
print("=" * 70)

print(f"Produits : {len(products)}")

# ---------------------------------------------------------
# Compteurs
# ---------------------------------------------------------

total_variants = 0
total_images = 0

missing_description = []
missing_product_sku = []
missing_variant_sku = []
missing_variant_price = []
missing_variant_id = []
missing_images = []
missing_category = []
missing_currency = []

invalid_sale_price = []
invalid_regular_price = []

product_ids = []
slugs = []
product_skus = []
variant_skus = []
variant_ids = []

anomalies = []

# ---------------------------------------------------------
# Analyse
# ---------------------------------------------------------

for p in products:

    slug = p.get("slug") or p.get("handle") or ""
    title = p.get("name") or p.get("title") or slug

    if slug:
        slugs.append(slug)

    # Description
    description = (p.get("description") or "").strip()

    if not description:
        missing_description.append(slug)

    # SKU produit
    sku = (p.get("sku") or "").strip()

    if sku:
        product_skus.append(sku)
    else:
        missing_product_sku.append(slug)

    # ID Shopify
    pid = p.get("shopify_id") or p.get("id")

    if pid is not None:
        product_ids.append(str(pid))

    # Catégorie
    category = p.get("category")

    if not category:
        missing_category.append(slug)

    # Devise
    currency = p.get("currency")

    if not currency:
        missing_currency.append(slug)

    # Images
    images = p.get("images") or []

    if not images:
        missing_images.append(slug)

    total_images += len(images)

    # Variantes
    variants = p.get("variants") or []

    total_variants += len(variants)

    for v in variants:

        vid = v.get("id") or v.get("shopify_id")

        if vid is None:
            missing_variant_id.append(f"{slug}")

        else:
            variant_ids.append(str(vid))

        vsku = (v.get("sku") or "").strip()

        if not vsku:
            missing_variant_sku.append(
                f"{slug} → variante {v.get('title', '')}"
            )
        else:
            variant_skus.append(vsku)

        price = v.get("price")

        if price in (None, ""):
            missing_variant_price.append(
                f"{slug} → variante {v.get('title', '')}"
            )

        regular = v.get("regular_price")
        sale = v.get("sale_price")

        try:
            if regular not in (None, "") and sale not in (None, ""):
                if float(sale) > float(regular):
                    invalid_sale_price.append(
                        f"{slug} → sale {sale} > regular {regular}"
                    )
        except:
            pass

    # Produit variable sans variantes
    product_type = p.get("type", "")

    if product_type == "variable" and not variants:
        anomalies.append(
            f"{slug} : produit variable sans variantes"
        )

# ---------------------------------------------------------
# Doublons
# ---------------------------------------------------------

def duplicates(items):
    c = Counter(items)
    return sorted([x for x, n in c.items() if n > 1])

duplicate_ids = duplicates(product_ids)
duplicate_slugs = duplicates(slugs)
duplicate_product_skus = duplicates(product_skus)
duplicate_variant_skus = duplicates(variant_skus)
duplicate_variant_ids = duplicates(variant_ids)

# ---------------------------------------------------------
# Affichage
# ---------------------------------------------------------

print()
print("-" * 70)
print("STRUCTURE")
print("-" * 70)

print(f"Variantes totales        : {total_variants}")
print(f"Images totales           : {total_images}")

print()
print("-" * 70)
print("CHAMPS MANQUANTS")
print("-" * 70)

print(f"Descriptions absentes    : {len(missing_description)}")
print(f"SKU produit absents     : {len(missing_product_sku)}")
print(f"SKU variantes absents   : {len(missing_variant_sku)}")
print(f"Prix variantes absents  : {len(missing_variant_price)}")
print(f"ID variantes absents    : {len(missing_variant_id)}")
print(f"Images absentes          : {len(missing_images)}")
print(f"Catégories absentes      : {len(missing_category)}")
print(f"Devises absentes         : {len(missing_currency)}")

print()
print("-" * 70)
print("DOUBLONS")
print("-" * 70)

print(f"IDs produits dupliqués   : {len(duplicate_ids)}")
print(f"Slugs dupliqués          : {len(duplicate_slugs)}")
print(f"SKU produits dupliqués   : {len(duplicate_product_skus)}")
print(f"SKU variantes dupliqués  : {len(duplicate_variant_skus)}")
print(f"IDs variantes dupliqués  : {len(duplicate_variant_ids)}")

print()
print("-" * 70)
print("PRIX")
print("-" * 70)

print(f"Promotions incohérentes  : {len(invalid_sale_price)}")

print()
print("-" * 70)
print("ANOMALIES STRUCTURELLES")
print("-" * 70)

print(f"Anomalies                : {len(anomalies)}")

# ---------------------------------------------------------
# Détails
# ---------------------------------------------------------

if missing_description:
    print()
    print(">>> PRODUITS SANS DESCRIPTION")
    for x in missing_description:
        print(" -", x)

if missing_product_sku:
    print()
    print(">>> PRODUITS SANS SKU")
    for x in missing_product_sku:
        print(" -", x)

if missing_variant_sku:
    print()
    print(">>> VARIANTES SANS SKU")
    for x in missing_variant_sku:
        print(" -", x)

if missing_variant_price:
    print()
    print(">>> VARIANTES SANS PRIX")
    for x in missing_variant_price:
        print(" -", x)

if duplicate_product_skus:
    print()
    print(">>> SKU PRODUITS DUPLIQUÉS")
    for x in duplicate_product_skus:
        print(" -", x)

if duplicate_variant_skus:
    print()
    print(">>> SKU VARIANTES DUPLIQUÉS")
    for x in duplicate_variant_skus:
        print(" -", x)

if duplicate_slugs:
    print()
    print(">>> SLUGS DUPLIQUÉS")
    for x in duplicate_slugs:
        print(" -", x)

if duplicate_ids:
    print()
    print(">>> IDs PRODUITS DUPLIQUÉS")
    for x in duplicate_ids:
        print(" -", x)

if invalid_sale_price:
    print()
    print(">>> PRIX PROMOTIONNELS INCOHÉRENTS")
    for x in invalid_sale_price:
        print(" -", x)

if anomalies:
    print()
    print(">>> ANOMALIES")
    for x in anomalies:
        print(" -", x)

# ---------------------------------------------------------
# Verdict
# ---------------------------------------------------------

critical = (
    missing_variant_price
    or duplicate_variant_skus
    or duplicate_variant_ids
    or duplicate_slugs
    or invalid_sale_price
    or anomalies
)

print()
print("=" * 70)

if critical:
    print("VERDICT : ⚠️ À CORRIGER AVANT IMPORT")
else:
    print("VERDICT : ✅ CATALOGUE STRUCTURELLEMENT PRÊT")

print("=" * 70)
