import re
import os
import shutil
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

html_files = list(ROOT.rglob("*.html"))

total_before = 0
total_after = 0
removed_blocks = 0
changed_files = 0
errors = 0

print(f"HTML à traiter : {len(html_files)}")
print("Nettoyage en place démarré...\n")

for i, path in enumerate(html_files, 1):

    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
        before = len(html.encode("utf-8"))

        file_removed_blocks = 0

        def repl(match):
            nonlocal_dummy = None
            global_removed = False

            block = match.group(0)
            low = block.lower()

            if any(k in low for k in REMOVE):
                return ""

            return block

        cleaned = SCRIPT_RE.sub(repl, html)

        after = len(cleaned.encode("utf-8"))

        total_before += before
        total_after += after

        if after < before:
            tmp = path.with_suffix(".tmp")

            tmp.write_text(
                cleaned,
                encoding="utf-8"
            )

            os.replace(tmp, path)

            changed_files += 1
            removed_blocks += sum(
                1 for block in SCRIPT_RE.findall(html)
                if any(k in block.lower() for k in REMOVE)
            )

        if i % 250 == 0 or i == len(html_files):
            saved = total_before - total_after

            print(
                f"[{i}/{len(html_files)}] "
                f"modifiés={changed_files} | "
                f"récupérés={saved/1024/1024/1024:.2f} Go"
            )

    except Exception as e:
        errors += 1
        print(f"ERREUR : {path} -> {e}")

print("\n" + "=" * 70)
print("NETTOYAGE TERMINÉ")
print("=" * 70)

print(f"Fichiers analysés   : {len(html_files)}")
print(f"Fichiers modifiés   : {changed_files}")
print(f"Blocs supprimés     : {removed_blocks}")
print(f"Taille avant        : {total_before/1024/1024/1024:.2f} Go")
print(f"Taille après        : {total_after/1024/1024/1024:.2f} Go")
print(f"Espace récupéré     : {(total_before-total_after)/1024/1024/1024:.2f} Go")
print(f"Erreurs             : {errors}")
print("=" * 70)
