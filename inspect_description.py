from pathlib import Path
from bs4 import BeautifulSoup
import re

files = [
    Path("site/de/products/buture-2-in-1-brush-for-vc90-vacuum/index.html"),
    Path("site/de/products/bp20-cordless-vacuum-cleaner/index.html"),
    Path("site/de/products/bp10-battery/index.html"),
]

for path in files:

    print("\n" + "=" * 100)
    print(path)
    print("=" * 100)

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # --------------------------------------------------
    # TITRE
    # --------------------------------------------------

    h1 = soup.find("h1")
    print("\n[H1]")
    print(h1.get_text(" ", strip=True)[:500] if h1 else "ABSENT")

    # --------------------------------------------------
    # META DESCRIPTION
    # --------------------------------------------------

    meta = soup.find("meta", attrs={"name": "description"})
    print("\n[META DESCRIPTION]")
    print(meta.get("content", "")[:1000] if meta else "ABSENT")

    # --------------------------------------------------
    # SELECTEURS DESCRIPTION
    # --------------------------------------------------

    selectors = [
        ".product-info__description",
        ".product__description",
        ".product-description",
        "[class*='product-info__description']",
        "[class*='product-description']",
        "[class*='product__description']",
        "[class*='description']",
        "[class*='Description']",
        ".accordion",
        "[class*='accordion']",
        ".product-info",
        "[class*='product-info']",
    ]

    print("\n[SELECTEURS]")

    seen = set()

    for selector in selectors:

        try:
            elements = soup.select(selector)
        except Exception:
            continue

        for el in elements:

            text = el.get_text(" ", strip=True)

            if len(text) < 30:
                continue

            key = text[:300]

            if key in seen:
                continue

            seen.add(key)

            print("\n---", selector, "---")
            print("LONGUEUR :", len(text))
            print(text[:2000])

    # --------------------------------------------------
    # BLOCS CONTENANT LE TITRE DU PRODUIT
    # --------------------------------------------------

    if h1:

        title_words = h1.get_text(" ", strip=True).split()

        print("\n[RECHERCHE TEXTE PRODUIT]")

        # recherche avec quelques mots significatifs
        words = [
            w for w in title_words
            if len(w) >= 5
            and w.lower() not in {
                "buture",
                "staubsauger",
                "vakuum",
                "für"
            }
        ][:4]

        for word in words:

            print(f"\n### MOT : {word}")

            matches = soup.find_all(
                string=re.compile(re.escape(word), re.I)
            )

            count = 0

            for match in matches[:10]:

                parent = match.parent

                if not parent:
                    continue

                text = parent.get_text(" ", strip=True)

                if len(text) < 40:
                    continue

                print("\nTAG :", parent.name)
                print("CLASS :", parent.get("class"))
                print("ID :", parent.get("id"))
                print("TEXT :", text[:1500])

                count += 1

                if count >= 5:
                    break

    # --------------------------------------------------
    # JSON-LD
    # --------------------------------------------------

    print("\n[JSON-LD]")

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    ):

        text = script.string or script.get_text()

        if not text:
            continue

        if "description" in text.lower():

            print(text[:5000])

    print("\n" + "-" * 100)
