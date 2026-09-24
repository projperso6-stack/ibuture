from pathlib import Path
from urllib.parse import urlparse

missing_file = Path("missing_urls.txt")

urls = [
    u.strip()
    for u in missing_file.read_text(encoding="utf-8").splitlines()
    if u.strip()
]

default = []

for url in urls:
    path = urlparse(url).path.strip("/")

    # uniquement les URLs sans préfixe de langue/marché
    if not path:
        continue

    first = path.split("/")[0]

    # Les versions localisées commencent par ces préfixes
    locales = {
        "de", "fr", "pl", "es", "it",
        "de-de", "fr-de", "pl-de", "es-de", "it-de", "en-de",
        "de-es", "fr-es", "pl-es", "es-es", "it-es", "en-es",
        "de-it", "fr-it", "pl-it", "es-it", "it-it", "en-it",
        "de-fr", "fr-fr", "pl-fr", "es-fr", "it-fr", "en-fr",
        "de-pl", "fr-pl", "pl-pl", "es-pl", "it-pl", "en-pl",
        "de-nl", "fr-nl", "pl-nl", "es-nl", "it-nl", "en-nl",
        "de-at", "fr-at", "pl-at", "es-at", "it-at", "en-at",
        "de-lu", "fr-lu", "pl-lu", "es-lu", "it-lu", "en-lu",
    }

    if first not in locales:
        default.append(url)

print()
print("=" * 70)
print("VERSION PAR DÉFAUT")
print("=" * 70)

print(f"Pages manquantes sans préfixe : {len(default)}")

from collections import Counter

types = Counter()

for url in default:
    path = urlparse(url).path

    if "/products/" in path:
        types["products"] += 1
    elif "/collections/" in path:
        types["collections"] += 1
    elif "/blogs/" in path:
        types["blogs"] += 1
    elif "/pages/" in path:
        types["pages"] += 1
    elif path.endswith("/agents.md"):
        types["agents"] += 1
    else:
        types["autres"] += 1

print()
for typ, count in types.most_common():
    print(f"{typ:15} : {count}")

Path("missing_default.txt").write_text(
    "\n".join(default) + "\n",
    encoding="utf-8"
)

print()
print("Liste créée : missing_default.txt")
print("=" * 70)
