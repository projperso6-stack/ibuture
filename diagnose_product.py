import re
import json
from pathlib import Path
from bs4 import BeautifulSoup

files = [
    Path("site/de/products/bp20-cordless-vacuum-cleaner/index.html"),
    Path("site/de/products/bp10-battery/index.html"),
    Path("site/de/products/buture-2-in-1-brush-for-vc90-vacuum/index.html"),
]

for path in files:

    print("\n" + "=" * 80)
    print(path)
    print("=" * 80)

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # ---------------------------------------------------------
    # 1. Toutes les occurrences storefrontCurrency
    # ---------------------------------------------------------

    print("\n[1] storefrontCurrency")

    matches = list(re.finditer(
        r".{0,150}storefrontCurrency.{0,150}",
        html,
        re.I | re.S
    ))

    if not matches:
        print("Aucune occurrence")

    for m in matches[:20]:
        print(
            re.sub(r"\s+", " ", m.group(0))
        )

    # ---------------------------------------------------------
    # 2. Toutes les devises explicites
    # ---------------------------------------------------------

    print("\n[2] Occurrences de EUR / USD")

    for pattern in [
        r".{0,100}EUR.{0,100}",
        r".{0,100}USD.{0,100}",
        r".{0,100}€.{0,100}",
        r".{0,100}\$.{0,100}",
    ]:

        print("\nPATTERN:", pattern)

        found = list(re.finditer(
            pattern,
            html,
            re.I | re.S
        ))

        for m in found[:10]:
            print(
                re.sub(r"\s+", " ", m.group(0))
            )

    # ---------------------------------------------------------
    # 3. Meta prix
    # ---------------------------------------------------------

    print("\n[3] META PRICE")

    for tag in soup.find_all("meta"):

        attrs = str(tag.attrs).lower()

        if (
            "price" in attrs
            or "currency" in attrs
        ):
            print(tag)

    # ---------------------------------------------------------
    # 4. Scripts contenant currency
    # ---------------------------------------------------------

    print("\n[4] SCRIPTS contenant currency")

    count = 0

    for script in soup.find_all("script"):

        text = script.string or script.get_text()

        if "currency" in text.lower():

            print("\n--- SCRIPT ---")

            snippets = re.findall(
                r".{0,200}currency.{0,300}",
                text,
                re.I | re.S
            )

            for snippet in snippets[:5]:
                print(
                    re.sub(r"\s+", " ", snippet)
                )

            count += 1

            if count >= 10:
                break

    # ---------------------------------------------------------
    # 5. Données appBlockPlacements
    # ---------------------------------------------------------

    print("\n[5] appBlockPlacements")

    m = re.search(
        r"window\.appBlockPlacements\s*=\s*(.*?);",
        html,
        re.I | re.S
    )

    if m:

        block = m.group(1)

        print(
            re.sub(r"\s+", " ", block[:5000])
        )

    else:

        print("appBlockPlacements non trouvé")

