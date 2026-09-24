import re
from pathlib import Path
from bs4 import BeautifulSoup

SITE = Path("site")

PRODUCTS = [
    SITE / "de/products/bp20-cordless-vacuum-cleaner/index.html",
    SITE / "de/products/bp10-battery/index.html",
    SITE / "de/products/bp10-roller-brush/index.html",
]


def compact(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


for path in PRODUCTS:

    print("\n")
    print("=" * 90)
    print("PRODUIT :", path)
    print("=" * 90)

    if not path.exists():
        print("FICHIER INTROUVABLE")
        continue

    html = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    soup = BeautifulSoup(html, "html.parser")

    # -------------------------------------------------
    # TITRE
    # -------------------------------------------------

    print("\n[TITRE]")

    title = soup.find("h1")

    if title:
        print("H1 :", compact(title.get_text(" ", strip=True)))

    # -------------------------------------------------
    # META DESCRIPTION
    # -------------------------------------------------

    print("\n[META]")

    meta_desc = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta_desc:
        print(
            "description :",
            compact(meta_desc.get("content"))
        )

    # -------------------------------------------------
    # BREADCRUMB
    # -------------------------------------------------

    print("\n[BREADCRUMB / NAVIGATION]")

    for tag in soup.find_all(
        ["nav", "ol", "ul"],
        limit=100
    ):

        text = compact(tag.get_text(" ", strip=True))

        if not text:
            continue

        low = text.lower()

        keywords = [
            "home",
            "startseite",
            "shop",
            "staubsauger",
            "zubehör",
            "accessories",
            "vacuum",
            "batter"
        ]

        if any(k in low for k in keywords):

            classes = " ".join(tag.get("class", []))

            print(
                "TAG:",
                tag.name,
                "| CLASS:",
                classes[:200]
            )

            print(
                "TEXT:",
                text[:500]
            )

    # -------------------------------------------------
    # BLOCS CONTENANT "DESCRIPTION"
    # -------------------------------------------------

    print("\n[BLOCS AVEC 'DESCRIPTION']")

    found = 0

    for tag in soup.find_all(True):

        attrs = " ".join(
            [
                str(tag.get("id", "")),
                " ".join(tag.get("class", []))
            ]
        )

        if "description" not in attrs.lower():
            continue

        text = compact(tag.get_text(" ", strip=True))

        if len(text) < 20:
            continue

        print("\nTAG:", tag.name)
        print("ATTRS:", attrs[:500])
        print("TEXT:", text[:1000])

        found += 1

        if found >= 15:
            break

    # -------------------------------------------------
    # BLOCS PRODUIT
    # -------------------------------------------------

    print("\n[BLOCS AVEC 'product']")

    found = 0

    for tag in soup.find_all(True):

        attrs = " ".join(
            [
                str(tag.get("id", "")),
                " ".join(tag.get("class", []))
            ]
        )

        if "product" not in attrs.lower():
            continue

        text = compact(tag.get_text(" ", strip=True))

        if len(text) < 30:
            continue

        print("\nTAG:", tag.name)
        print("ATTRS:", attrs[:500])
        print("TEXT:", text[:700])

        found += 1

        if found >= 20:
            break

    # -------------------------------------------------
    # JSON-LD
    # -------------------------------------------------

    print("\n[JSON-LD]")

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        text = compact(script.get_text())

        if not text:
            continue

        print(text[:1500])
        print("---")

    print("\nFIN :", path)
