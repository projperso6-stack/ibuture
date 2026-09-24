import re
from pathlib import Path

ROOT = Path("site")

files = [
    ROOT / "products/buture-charger-for-vc90-vacuum/index.html",
    ROOT / "collections/vacuum-bundles/index.html",
    ROOT / "blogs/all/index.html",
    ROOT / "pages/warranty/index.html",
    ROOT / "pages/rewards/index.html",
]

SCRIPT_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>",
    re.I | re.S
)

REMOVE = [
    "window.langshopconfig",
    "wpmloader",
    "shortly-version",
    "jdgmsettings",
]

checks = {
    "prix": [
        "price", "product:price", "priceamount",
        "money", "currency"
    ],
    "variante": [
        "variant", "variants", "product-form"
    ],
    "panier": [
        "add-to-cart", "add_to_cart",
        "addtocart", "cart"
    ],
    "images": [
        "<img", "srcset"
    ],
    "description": [
        "description", "product-description"
    ],
    "seo": [
        'application/ld+json'
    ],
}

def clean(html):
    removed = 0

    def repl(match):
        nonlocal removed
        block = match.group(0)
        low = block.lower()

        if any(x in low for x in REMOVE):
            removed += 1
            return ""

        return block

    return SCRIPT_RE.sub(repl, html), removed


print("=" * 75)
print("VERIFICATION DU NETTOYAGE")
print("AUCUN FICHIER ORIGINAL N'EST MODIFIÉ")
print("=" * 75)

for path in files:

    if not path.exists():
        print("\nABSENT :", path)
        continue

    html = path.read_text(encoding="utf-8", errors="ignore")
    cleaned, removed = clean(html)

    original_size = len(html.encode())
    clean_size = len(cleaned.encode())
    gain = original_size - clean_size

    print("\n" + "-" * 75)
    print(path)

    print(
        f"Taille : {original_size/1024:.1f} KB"
        f" -> {clean_size/1024:.1f} KB"
        f" | gain : {gain/1024:.1f} KB"
    )

    print(f"Blocs supprimés : {removed}")

    for name, terms in checks.items():

        found = any(term.lower() in cleaned.lower() for term in terms)

        status = "OK" if found else "ATTENTION"

        print(f"  {name:15s}: {status}")

print("\n" + "=" * 75)
print("FIN — site/ n'a pas été modifié")
print("=" * 75)
