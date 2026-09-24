import os
import re
import json
from bs4 import BeautifulSoup

SITE = "site/de/products"
OUTPUT = "products_sample_v5.json"
LIMIT = 200


def clean_text(value):
    if not value:
        return ""

    soup = BeautifulSoup(str(value), "html.parser")

    # Supprimer scripts/styles éventuels
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def is_generic_description(text):
    if not text:
        return True

    t = text.lower()

    generic_patterns = [
        "buture focuses on providing",
        "high-performance vacuum cleaners",
        "explore our product range",
        "shopify",
        "customer support",
        "marketing",
        "analytics",
        "loyalty",
        "payment",
        "shipping",
    ]

    return any(p in t for p in generic_patterns)


def extract_json_ld(soup):
    results = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()

        try:
            data = json.loads(raw)
        except Exception:
            continue

        if isinstance(data, list):
            results.extend(data)

        elif isinstance(data, dict) and "@graph" in data:
            graph = data["@graph"]
            if isinstance(graph, list):
                results.extend(graph)
            else:
                results.append(graph)

        elif isinstance(data, dict):
            results.append(data)

    return results


def find_product_json_ld(jsonlds):
    products = []

    for item in jsonlds:
        if not isinstance(item, dict):
            continue

        typ = item.get("@type", "")

        if typ in ("Product", "ProductGroup"):
            products.append(item)

    return products


def extract_product_description(soup, xcotton, jsonlds):
    candidates = []

    # ---------------------------------------------------------
    # 1. Description Shopify xcotton
    # ---------------------------------------------------------
    desc = xcotton.get("description")

    if isinstance(desc, str):
        text = clean_text(desc)

        if text and not is_generic_description(text):
            candidates.append({
                "text": text,
                "source": "xcotton",
                "score": 100
            })

    # ---------------------------------------------------------
    # 2. Description Product / ProductGroup JSON-LD
    # ---------------------------------------------------------
    for product in find_product_json_ld(jsonlds):
        desc = product.get("description")

        if isinstance(desc, str):
            text = clean_text(desc)

            if text and not is_generic_description(text):
                candidates.append({
                    "text": text,
                    "source": "jsonld_product",
                    "score": 90
                })

    # ---------------------------------------------------------
    # 3. Sélecteurs HTML réellement orientés description
    # ---------------------------------------------------------
    selectors = [
        ".product-info__description",
        ".product__description",
        ".product-description",
        ".product__description-content",
        "[class*='product-description']",
        "[class*='product__description']",
        "[data-product-description]",
    ]

    for selector in selectors:
        try:
            nodes = soup.select(selector)
        except Exception:
            continue

        for node in nodes:
            text = clean_text(node)

            # Éviter les blocs gigantesques contenant toute l'interface
            if 80 <= len(text) <= 50000 and not is_generic_description(text):

                # Éviter les faux positifs clairement liés au panier
                bad_words = [
                    "add to cart",
                    "buy it now",
                    "quantity",
                    "subtotal",
                    "checkout",
                    "shipping",
                    "klarna",
                ]

                lower = text.lower()

                if not any(word in lower for word in bad_words):
                    candidates.append({
                        "text": text,
                        "source": f"html:{selector}",
                        "score": 80
                    })

    # ---------------------------------------------------------
    # 4. Meta description = dernier vrai fallback
    # ---------------------------------------------------------
    meta = soup.find("meta", attrs={"name": "description"})

    if meta and meta.get("content"):
        text = clean_text(meta.get("content"))

        if text and not is_generic_description(text):
            candidates.append({
                "text": text,
                "source": "meta_fallback",
                "score": 40
            })

    # ---------------------------------------------------------
    # Choix final
    # ---------------------------------------------------------
    if not candidates:
        return {
            "description": "",
            "description_source": "none",
            "description_length": 0
        }

    # priorité score puis longueur
    candidates.sort(
        key=lambda x: (x["score"], len(x["text"])),
        reverse=True
    )

    best = candidates[0]

    # Classification
    if best["source"] == "meta_fallback":
        source = "meta_fallback"

    elif len(best["text"]) < 300:
        source = "short"

    else:
        source = "full"

    return {
        "description": best["text"],
        "description_source": source,
        "description_origin": best["source"],
        "description_length": len(best["text"])
    }


def extract_xcotton(soup):
    script = soup.find(
        "script",
        id="xcotton_pp_variants"
    )

    if not script:
        return {}

    raw = script.string or script.get_text()

    try:
        return json.loads(raw)
    except Exception:
        return {}


def extract_currency(soup):
    # 1. storefrontCurrency
    text = soup.get_text(" ", strip=False)

    patterns = [
        r'"storefrontCurrency"\s*:\s*"([A-Z]{3})"',
        r"'storefrontCurrency'\s*:\s*'([A-Z]{3})'",
        r'"currency"\s*:\s*"([A-Z]{3})"',
        r"'currency'\s*:\s*'([A-Z]{3})'",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1)

    # 2. meta price currency
    meta = soup.find(
        "meta",
        attrs={"property": "product:price:currency"}
    )

    if meta and meta.get("content"):
        return meta["content"].upper()

    # 3. JSON-LD
    for item in extract_json_ld(soup):
        if not isinstance(item, dict):
            continue

        offers = item.get("offers")

        if isinstance(offers, dict):
            currency = offers.get("priceCurrency")

            if currency:
                return str(currency).upper()

        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    currency = offer.get("priceCurrency")

                    if currency:
                        return str(currency).upper()

    return ""


def classify_product(xcotton):
    variants = xcotton.get("variants") or []
    options = xcotton.get("options") or []

    if len(variants) > 1:
        return "variable"

    if len(variants) == 0:
        return "simple"

    if options == ["Title"]:
        return "simple"

    variant_title = variants[0].get("title", "")

    if variant_title in ("Default Title", ""):
        return "simple"

    return "simple"


def extract_product(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    xcotton = extract_xcotton(soup)
    jsonlds = extract_json_ld(soup)

    title = (
        xcotton.get("title")
        or (
            soup.find("meta", property="og:title") or {}
        ).get("content")
        or ""
    )

    h1 = soup.find("h1")
    h1_text = clean_text(h1) if h1 else ""

    handle = xcotton.get("handle")

    if not handle:
        handle = os.path.basename(os.path.dirname(path))

    variants = xcotton.get("variants") or []
    images = xcotton.get("images") or []

    if not images:
        # fallback images
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")

            if src and "cdn/shop" in src:
                images.append(src)

    # dédoublonnage
    clean_images = []

    for img in images:
        if img and img not in clean_images:
            clean_images.append(img)

    desc = extract_product_description(
        soup,
        xcotton,
        jsonlds
    )

    product_type = xcotton.get("type") or ""

    currency = extract_currency(soup)

    return {
        "handle": handle,
        "title": clean_text(title),
        "h1": h1_text,
        "vendor": xcotton.get("vendor", ""),
        "category": product_type,
        "type": classify_product(xcotton),
        "currency": currency,
        "price": xcotton.get("price"),
        "price_min": xcotton.get("price_min"),
        "price_max": xcotton.get("price_max"),
        "compare_at_price": xcotton.get("compare_at_price"),
        "available": xcotton.get("available"),
        "options": xcotton.get("options") or [],
        "variants": variants,
        "images": clean_images,
        **desc
    }


# ============================================================
# MAIN
# ============================================================

product_dirs = []

if os.path.isdir(SITE):

    for name in os.listdir(SITE):

        path = os.path.join(SITE, name)

        if os.path.isdir(path):
            index = os.path.join(path, "index.html")

            if os.path.isfile(index):
                product_dirs.append(index)

product_dirs.sort()

print(f"Produits trouvés : {len(product_dirs)}")

selected = product_dirs[:LIMIT]

print(f"Extraction de {len(selected)} produits")
print()

products = []
errors = []

stats = {
    "full": 0,
    "short": 0,
    "meta_fallback": 0,
    "none": 0,
    "variable": 0,
    "simple": 0,
    "missing_images": 0,
    "missing_category": 0,
    "missing_currency": 0,
}


for i, path in enumerate(selected, 1):

    try:
        product = extract_product(path)
        products.append(product)

        source = product["description_source"]

        stats[source] = stats.get(source, 0) + 1

        ptype = product["type"]
        stats[ptype] = stats.get(ptype, 0) + 1

        if not product["images"]:
            stats["missing_images"] += 1

        if not product["category"]:
            stats["missing_category"] += 1

        if not product["currency"]:
            stats["missing_currency"] += 1

        print(
            f"[{i:03d}] "
            f"{product['handle']} | "
            f"{ptype} | "
            f"{product['currency'] or '???'} | "
            f"{len(product['variants'])} var | "
            f"{len(product['images'])} img | "
            f"desc={product['description_length']} "
            f"[{source}]"
        )

    except Exception as e:

        errors.append({
            "path": path,
            "error": str(e)
        })

        print(
            f"[{i:03d}] ERREUR | "
            f"{os.path.basename(os.path.dirname(path))} | "
            f"{e}"
        )


output = {
    "version": "v5",
    "limit": LIMIT,
    "total_found": len(product_dirs),
    "total_extracted": len(products),
    "stats": stats,
    "errors": errors,
    "products": products
}


with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("=" * 60)
print("RÉSULTAT V5")
print("=" * 60)

print(f"Produits extraits : {len(products)}")
print(f"Erreurs            : {len(errors)}")
print()

print("Descriptions :")
print(f"  🟢 full          : {stats.get('full', 0)}")
print(f"  🟡 short         : {stats.get('short', 0)}")
print(f"  🟠 meta_fallback : {stats.get('meta_fallback', 0)}")
print(f"  🔴 none          : {stats.get('none', 0)}")

print()
print("Produits :")
print(f"  variables : {stats.get('variable', 0)}")
print(f"  simples   : {stats.get('simple', 0)}")

print()
print("Contrôles :")
print(f"  images manquantes   : {stats.get('missing_images', 0)}")
print(f"  catégories manquantes : {stats.get('missing_category', 0)}")
print(f"  devises manquantes  : {stats.get('missing_currency', 0)}")

print()
print(f"Fichier créé : {OUTPUT}")
