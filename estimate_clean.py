import re
from pathlib import Path

ROOT = Path("site")

SCRIPT_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>",
    re.IGNORECASE | re.DOTALL
)

REMOVE = [
    "window.langshopconfig",
    "wpmloader",
    "shortly-version",
    "jdgmsettings",
]

total_original = 0
total_clean = 0
total_removed = 0
files = 0
blocks = 0

html_files = list(ROOT.rglob("*.html"))

print(f"HTML trouvés : {len(html_files)}")
print("Calcul en cours...\n")

for path in html_files:
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    original = len(html.encode("utf-8"))

    removed_here = 0
    removed_blocks = 0

    def repl(match):
        nonlocal_dummy = None
        global blocks

        block = match.group(0)
        low = block.lower()

        if any(k in low for k in REMOVE):
            return ""

        return block

    cleaned = SCRIPT_RE.sub(repl, html)

    clean_size = len(cleaned.encode("utf-8"))

    total_original += original
    total_clean += clean_size
    total_removed += original - clean_size
    files += 1

    # Comptage exact des blocs
    for script in SCRIPT_RE.findall(html):
        if any(k in script.lower() for k in REMOVE):
            removed_blocks += 1

    blocks += removed_blocks

print("=" * 70)
print("ESTIMATION DU NETTOYAGE GLOBAL")
print("=" * 70)

print(f"Fichiers HTML analysés : {files}")
print(f"Taille HTML actuelle   : {total_original / 1024 / 1024 / 1024:.2f} GB")
print(f"Taille après nettoyage : {total_clean / 1024 / 1024 / 1024:.2f} GB")
print(f"Espace récupérable    : {total_removed / 1024 / 1024 / 1024:.2f} GB")

if total_original:
    pct = total_removed / total_original * 100
    print(f"Réduction HTML        : {pct:.2f} %")

print(f"Blocs supprimables    : {blocks}")

print("=" * 70)
print("AUCUN FICHIER N'A ÉTÉ MODIFIÉ.")
print("=" * 70)
