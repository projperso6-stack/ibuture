import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

products = list(Path("site").glob("*/products/*/index.html"))

if not products:
    print("Aucun produit trouvé.")
    raise SystemExit(1)

# Prendre plusieurs produits différents
samples = products[:10]

for path in samples:
    print("\n" + "=" * 80)
    print("FICHIER :", path)
    print("=" * 80)

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # TITLE
    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    # H1
    h1 = soup.find("h1")
    product_name = h1.get_text(" ", strip=True) if h1 else ""

    print("TITLE       :", title[:150])
    print("H1          :", product_name[:150])

    # JSON-LD
    jsonld_count = 0

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or script.get_text())
            jsonld_count += 1

            if isinstance(data, dict):
                print("JSON-LD TYPE:", data.get("@type"))
                print("JSON-LD NAME :", str(data.get("name", ""))[:120])
                print("JSON-LD SKU  :", data.get("sku", ""))

                offers = data.get("offers")

                if isinstance(offers, dict):
                    print("PRICE       :", offers.get("price"))
                    print("CURRENCY    :", offers.get("priceCurrency"))

                elif isinstance(offers, list) and offers:
                    print("OFFERS      :", len(offers))
                    print("FIRST PRICE :", offers[0].get("price"))
                    print("FIRST SKU   :", offers[0].get("sku"))

        except Exception:
            pass

    print("JSON-LD BLOCS:", jsonld_count)

    # Shopify product JSON
    patterns = [
        r'"product":\s*(\{.*?\})\s*,\s*"page"',
        r'var\s+meta\s*=\s*(\{.*?\});',
        r'product\s*=\s*(\{.*?\});'
    ]

    found = False

    for pattern in patterns:
        matches = re.findall(pattern, html, re.S)

        for match in matches:
            try:
                data = json.loads(match)

                if isinstance(data, dict) and (
                    "variants" in data or "handle" in data
                ):
                    print("\nSHOPIFY PRODUCT JSON")
                    print("HANDLE      :", data.get("handle"))
                    print("VENDOR      :", data.get("vendor"))
                    print("TYPE        :", data.get("type"))
                    print("TAGS        :", data.get("tags"))
                    print("VARIANTS    :", len(data.get("variants", [])))
                    print("IMAGES      :", len(data.get("images", [])))
                    print("OPTIONS     :", len(data.get("options", [])))

                    for variant in data.get("variants", [])[:10]:
                        print(
                            "  VARIANT:",
                            variant.get("id"),
                            "| SKU:",
                            variant.get("sku"),
                            "| PRICE:",
                            variant.get("price"),
                            "| COMPARE:",
                            variant.get("compare_at_price"),
                            "| TITLE:",
                            variant.get("title")
                        )

                    found = True
                    break

            except Exception:
                continue

        if found:
            break

    if not found:
        # Recherche brute de xcotton
        print(
            "xcotton_pp_variants :",
            html.lower().count("xcotton_pp_variants")
        )
