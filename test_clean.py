import re
from pathlib import Path

ROOT = Path("site")

# Pages représentatives
files = []

for pattern in [
    "products/*/index.html",
    "collections/*/index.html",
    "blogs/*/index.html",
    "pages/*/index.html",
]:
    found = list(ROOT.glob(pattern))
    files.extend(found[:3])

# Ajouter quelques pages localisées
for p in ROOT.glob("fr-*/products/*/index.html"):
    files.append(p)
    if len(files) >= 10:
        break

files = list(dict.fromkeys(files))[:10]

# Chaque bloc <script> est traité individuellement.
SCRIPT_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>",
    re.IGNORECASE | re.DOTALL
)

def get_scripts(html):
    return SCRIPT_RE.findall(html)

def remove_blocks(html, keywords):
    scripts = get_scripts(html)
    removed = []

    for script in scripts:
        low = script.lower()
        if any(k.lower() in low for k in keywords):
            removed.append(script)

    result = html
    for script in removed:
        result = result.replace(script, "", 1)

    return result, removed

tests = {
    "loyalty": ["window.loyalty_onsite"],
    "langshop": ["window.langshopconfig"],
    "tracking": ["wpmloader", "shortly-version"],
    "reviews": ["jdgmsettings"],
    "loyalty_langshop_tracking": [
        "window.loyalty_onsite",
        "window.langshopconfig",
        "wpmloader",
        "shortly-version",
    ],
    "loyalty_langshop_tracking_reviews": [
        "window.loyalty_onsite",
        "window.langshopconfig",
        "wpmloader",
        "shortly-version",
        "jdgmsettings",
    ],
}

print("=" * 75)
print("TEST NETTOYAGE V4 — AUCUN FICHIER ORIGINAL MODIFIÉ")
print("=" * 75)

for path in files:
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print("ERREUR:", path, e)
        continue

    original = len(html.encode("utf-8"))
    print("\n" + "-" * 75)
    print(path)
    print(f"Original : {original/1024:.2f} KB")

    for name, keywords in tests.items():
        cleaned, removed = remove_blocks(html, keywords)
        size = len(cleaned.encode("utf-8"))
        gain = original - size

        removed_size = sum(len(x.encode("utf-8")) for x in removed)

        print(
            f"{name:35s} : "
            f"{size/1024:8.2f} KB | "
            f"gain {gain/1024:8.2f} KB | "
            f"blocs supprimés {len(removed)}"
        )

        if removed:
            print(
                f"    taille blocs supprimés : "
                f"{removed_size/1024:.2f} KB"
            )

print("\n" + "=" * 75)
print("FIN DU TEST")
print("Le dossier site/ n'a PAS été modifié.")
print("=" * 75)
