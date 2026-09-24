from pathlib import Path
from bs4 import BeautifulSoup
import json
import re

BASE = Path("site/de/products")

PRODUCTS = [
    "bp20-vacuum-2-in-1-brush",
    "bp20-vacuum-battery",
    "x9-vacuum-main-body",
]


def clean_text(value):
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def show(label, text, max_len=1200):
    text = clean_text(text)
    print(f"\n--- {label} | {len(text)} caractères ---")
    if text:
        print(text[:max_len])
        if len(text) > max_len:
            print("...[tronqué]")
    else:
        print("(vide)")


def inspect_product(handle):
    path = BASE / handle / "index.html"

    print("\n" + "=" * 100)
    print(f"PRODUIT : {handle}")
    print(f"FICHIER  : {path}")
    print("=" * 100)

    if not path.exists():
        print("❌ Fichier introuvable")
        return

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # ---------------------------------------------------------
    # 1. Infos générales
    # ---------------------------------------------------------
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    h1 = soup.find("h1")
    meta_desc = soup.find("meta", attrs={"name": "description"})

    show("TITLE", title)
    show("H1", h1.get_text(" ", strip=True) if h1 else "")
    show("META DESCRIPTION", meta_desc.get("content", "") if meta_desc else "")

    # ---------------------------------------------------------
    # 2. Xcotton / données Shopify
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("XCOTTON / SHOPIFY PRODUCT DATA")
    print("-" * 80)

    xcotton = soup.find("script", id="xcotton_pp_variants")

    if xcotton:
        try:
            data = json.loads(xcotton.string or xcotton.get_text())

            print("✓ xcotton trouvé")
            print("Titre :", data.get("title"))
            print("Type  :", data.get("type"))
            print("Vendor:", data.get("vendor"))

            show("XCOTTON DESCRIPTION", data.get("description", ""), 2500)

            print("\nImages :", len(data.get("images", []) or []))
            print("Media  :", len(data.get("media", []) or []))
            print("Variants:", len(data.get("variants", []) or []))
            print("Options :", data.get("options"))

        except Exception as e:
            print("❌ Erreur JSON xcotton :", e)
    else:
        print("❌ xcotton_pp_variants introuvable")

    # ---------------------------------------------------------
    # 3. JSON-LD
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("JSON-LD")
    print("-" * 80)

    jsonld_count = 0

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()

        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:

            if not isinstance(item, dict):
                continue

            jsonld_count += 1

            typ = item.get("@type")
            desc = item.get("description")

            print(f"\n[{jsonld_count}] type = {typ}")

            if desc:
                show("JSON-LD DESCRIPTION", desc, 3000)

            if item.get("category"):
                print("category:", item.get("category"))

            if item.get("name"):
                print("name:", item.get("name"))

    if jsonld_count == 0:
        print("Aucun JSON-LD exploitable")

    # ---------------------------------------------------------
    # 4. Containers potentiels de description
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("CONTAINERS POTENTIELS")
    print("-" * 80)

    selectors = [
        ".product-info__description",
        ".product__description",
        ".product-description",
        ".product-description__content",
        "[class*='description']",
        "[id*='description']",
        "[class*='article']",
        "article",
        "main section",
    ]

    seen = set()

    for selector in selectors:

        elements = soup.select(selector)

        for el in elements:

            text = " ".join(el.get_text(" ", strip=True).split())

            if len(text) < 80:
                continue

            # éviter les énormes blocs UI
            if len(text) > 30000:
                continue

            key = text[:300]

            if key in seen:
                continue

            seen.add(key)

            classes = " ".join(el.get("class", []))
            element_id = el.get("id", "")

            print(
                f"\n[{selector}] "
                f"tag={el.name} "
                f"id={element_id!r} "
                f"class={classes!r} "
                f"len={len(text)}"
            )

            print(text[:1800])

    # ---------------------------------------------------------
    # 5. Accordéons / FAQ / informations produit
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("ACCORDÉONS / FAQ")
    print("-" * 80)

    accordion_selectors = [
        "[class*='accordion']",
        "[id*='accordion']",
        "details",
        "[class*='faq']",
        "[id*='faq']",
    ]

    acc_seen = set()

    for selector in accordion_selectors:

        for el in soup.select(selector):

            text = " ".join(el.get_text(" ", strip=True).split())

            if len(text) < 40 or len(text) > 15000:
                continue

            if text in acc_seen:
                continue

            acc_seen.add(text)

            print(
                f"\n[{selector}] "
                f"class={' '.join(el.get('class', []))!r} "
                f"len={len(text)}"
            )

            print(text[:2500])

    # ---------------------------------------------------------
    # 6. Scripts contenant "description"
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("SCRIPTS CONTENANT DES DONNÉES DE DESCRIPTION")
    print("-" * 80)

    count = 0

    for script in soup.find_all("script"):

        raw = script.string or script.get_text()

        if not raw:
            continue

        low = raw.lower()

        if "description" not in low:
            continue

        # on cherche des morceaux autour de "description"
        matches = list(re.finditer(r"description", raw, re.I))

        if not matches:
            continue

        count += 1

        print(
            f"\nSCRIPT #{count} "
            f"id={script.get('id')!r} "
            f"type={script.get('type')!r} "
            f"len={len(raw)}"
        )

        # afficher quelques occurrences
        for m in matches[:3]:
            start = max(0, m.start() - 250)
            end = min(len(raw), m.end() + 1000)

            snippet = raw[start:end]

            print("\n>>> occurrence")
            print(snippet[:1300])

    print("\n" + "=" * 100)
    print("FIN :", handle)
    print("=" * 100)


for product in PRODUCTS:
    inspect_product(product)

print("\nDiagnostic terminé.")
