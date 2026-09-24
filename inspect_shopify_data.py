import re
import json
from pathlib import Path
from bs4 import BeautifulSoup

path = next(Path("site").glob("*/products/*/index.html"))

html = path.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

print("=" * 80)
print("FICHIER :", path)
print("=" * 80)

# ---------------------------------------------------------
# 1. Tous les scripts contenant des mots-clés Shopify
# ---------------------------------------------------------

keywords = [
    "variants",
    "variant",
    "product",
    "featured_image",
    "compare_at_price",
    "inventory_quantity",
    "option1",
    "option2",
    "option3",
    "media",
    "images",
    "productJson",
]

found = []

for i, script in enumerate(soup.find_all("script")):
    text = script.string or script.get_text()

    if not text:
        continue

    matches = [k for k in keywords if k.lower() in text.lower()]

    if matches:
        found.append({
            "index": i,
            "size": len(text),
            "matches": matches,
            "type": script.get("type"),
            "id": script.get("id"),
        })

print("\n===== SCRIPTS SHOPIFY INTÉRESSANTS =====")

for x in sorted(found, key=lambda a: a["size"], reverse=True):
    print(
        f"script #{x['index']:3} | "
        f"{x['size']:9,} caractères | "
        f"type={x['type']} | "
        f"id={x['id']} | "
        f"{', '.join(x['matches'])}"
    )

# ---------------------------------------------------------
# 2. Recherche de blocs JSON contenant les variantes
# ---------------------------------------------------------

print("\n===== BLOCS CONTENANT LES INFORMATIONS VARIANTES =====")

counter = 0

for i, script in enumerate(soup.find_all("script")):

    text = script.string or script.get_text()

    if not text:
        continue

    if "variants" not in text.lower():
        continue

    # On affiche uniquement les blocs raisonnables
    if len(text) > 500000:
        continue

    counter += 1

    print("\n" + "-" * 80)
    print(f"SCRIPT #{i} — {len(text):,} caractères")
    print("-" * 80)

    # Afficher le début
    print(text[:5000])

    if counter >= 15:
        break

# ---------------------------------------------------------
# 3. Recherche de structures précises
# ---------------------------------------------------------

patterns = [
    r'"options"\s*:\s*\[[^\]]*\]',
    r'"images"\s*:\s*\[[^\]]*\]',
    r'"featured_image"\s*:\s*\{.*?\}',
    r'"inventory_quantity"\s*:\s*-?\d+',
    r'"compare_at_price"\s*:\s*[^,}]+',
    r'"public_title"\s*:\s*"[^"]*"',
    r'"name"\s*:\s*"[^"]*"',
]

print("\n===== STRUCTURES DÉTECTÉES =====")

for pattern in patterns:

    results = re.findall(pattern, html, flags=re.I | re.S)

    print(f"\nPATTERN : {pattern}")
    print("OCCURRENCES :", len(results))

    for result in results[:10]:
        print(" ", result[:1000])

# ---------------------------------------------------------
# 4. Attributs data-* liés aux variantes/images
# ---------------------------------------------------------

print("\n===== ATTRIBUTS DATA-* INTÉRESSANTS =====")

attrs = {}

for tag in soup.find_all(True):

    for name, value in tag.attrs.items():

        name_low = name.lower()

        if any(k in name_low for k in [
            "variant",
            "product",
            "image",
            "media",
            "option",
            "sku",
        ]):
            attrs[name] = attrs.get(name, 0) + 1

for name, count in sorted(attrs.items(), key=lambda x: -x[1]):
    print(f"{name:50} {count}")

print("\n===== FIN =====")
