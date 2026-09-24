import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

path = next(Path("site").glob("*/products/*/index.html"))

print("PRODUIT :", path)

html = path.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

result = {
    "file": str(path),
    "title": soup.title.get_text(" ", strip=True) if soup.title else None,
    "h1": None,
    "canonical": None,
    "product_json": None,
    "jsonld": [],
    "images": [],
    "prices_found": [],
    "skus_found": [],
}

# H1
h1 = soup.find("h1")
if h1:
    result["h1"] = h1.get_text(" ", strip=True)

# Canonical
canonical = soup.find("link", rel="canonical")
if canonical:
    result["canonical"] = canonical.get("href")

# Images
seen_images = set()

for img in soup.find_all("img"):
    for attr in ["src", "data-src", "data-original", "data-srcset"]:
        value = img.get(attr)
        if not value:
            continue

        # data-srcset peut contenir plusieurs URLs
        for item in value.split(","):
            url = item.strip().split(" ")[0]

            if url and url not in seen_images:
                seen_images.add(url)

                result["images"].append({
                    "url": url,
                    "alt": img.get("alt"),
                    "width": img.get("width"),
                    "height": img.get("height")
                })

# JSON-LD
for script in soup.find_all("script", type="application/ld+json"):
    try:
        raw = script.string or script.get_text()
        data = json.loads(raw)

        result["jsonld"].append(data)

    except Exception:
        pass

# Chercher les objets Shopify
patterns = [
    r'"product":\s*(\{.*?\})\s*,\s*"page"',
    r'var\s+meta\s*=\s*(\{.*?\});',
    r'product\s*=\s*(\{.*?\});'
]

for pattern in patterns:

    for match in re.findall(pattern, html, re.S):

        try:
            data = json.loads(match)

            if isinstance(data, dict) and (
                "variants" in data or "handle" in data
            ):
                result["product_json"] = data
                break

        except Exception:
            continue

    if result["product_json"]:
        break

# Prix
price_patterns = [
    r'"price"\s*:\s*"([^"]+)"',
    r'"price"\s*:\s*(\d+)',
    r'product:price:amount"\s+content="([^"]+)"'
]

for pattern in price_patterns:
    matches = re.findall(pattern, html, re.I)

    for value in matches:
        if value not in result["prices_found"]:
            result["prices_found"].append(value)

# SKU
for sku in re.findall(r'"sku"\s*:\s*"([^"]+)"', html, re.I):
    if sku not in result["skus_found"]:
        result["skus_found"].append(sku)

# Résumé
print("\n===== RÉSUMÉ =====")
print("H1          :", result["h1"])
print("CANONICAL   :", result["canonical"])
print("IMAGES      :", len(result["images"]))
print("JSON-LD     :", len(result["jsonld"]))
print("PRIX TROUVÉS:", len(result["prices_found"]))
print("SKUS TROUVÉS:", len(result["skus_found"]))

if result["product_json"]:
    p = result["product_json"]

    print("\n===== SHOPIFY =====")
    print("handle      :", p.get("handle"))
    print("vendor      :", p.get("vendor"))
    print("type        :", p.get("type"))
    print("tags        :", p.get("tags"))
    print("description :", bool(p.get("description")))
    print("variants    :", len(p.get("variants", [])))
    print("options     :", len(p.get("options", [])))
    print("images JSON :", len(p.get("images", [])))

    print("\n===== VARIANTES =====")

    for v in p.get("variants", []):

        print({
            "id": v.get("id"),
            "title": v.get("title"),
            "sku": v.get("sku"),
            "price": v.get("price"),
            "compare_at_price": v.get("compare_at_price"),
            "available": v.get("available"),
            "inventory_quantity": v.get("inventory_quantity"),
            "option1": v.get("option1"),
            "option2": v.get("option2"),
            "option3": v.get("option3"),
            "featured_image": v.get("featured_image")
        })

# Sauvegarde complète
Path("inspect_produit_result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("\nRésultat complet sauvegardé dans : inspect_produit_result.json")
