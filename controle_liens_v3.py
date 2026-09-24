import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from html import unescape
from collections import Counter

SITE = Path("site")
DOMAIN = "ibuture.com"

DYNAMIC_PREFIXES = (
    "/cart", "/checkout", "/account", "/search",
    "/apps", "/admin", "/challenge", "/password",
    "/customer_authentication", "/services"
)

NON_HTML_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".ico", ".css", ".js", ".json", ".xml", ".txt",
    ".pdf", ".zip", ".mp4", ".webm", ".mov",
    ".woff", ".woff2", ".ttf", ".eot"
}

LOCALE_RE = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$", re.I)

def normalize_path(href, base_url="https://ibuture.com/"):
    href = unescape(href).strip()

    if not href:
        return None

    if href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None

    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)

    if parsed.netloc and DOMAIN not in parsed.netloc.lower():
        return None

    path = unquote(parsed.path)

    if not path.startswith("/"):
        path = "/" + path

    path = re.sub(r"/+", "/", path)

    if not path.endswith("/") and not Path(path).suffix:
        path += "/"

    return path


def is_dynamic(path):
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in DYNAMIC_PREFIXES
    )


def is_locale_path(path):
    parts = [p for p in path.strip("/").split("/") if p]

    if not parts:
        return False

    return bool(LOCALE_RE.match(parts[0]))


def classify_page(path):
    if not path or is_dynamic(path):
        return None

    if is_locale_path(path):
        return None

    parts = [p for p in path.strip("/").split("/") if p]

    if not parts:
        return "root"

    # Produit
    if len(parts) == 2 and parts[0] == "products":
        slug = parts[1]
        if slug and slug not in {"index", "all"}:
            return "products"

    # Collection
    if len(parts) == 2 and parts[0] == "collections":
        slug = parts[1]
        if slug and slug not in {"index", "all"}:
            return "collections"

    # Page
    if len(parts) == 2 and parts[0] == "pages":
        slug = parts[1]
        if slug and slug not in {"index", "all"}:
            return "pages"

    # Article de blog
    if len(parts) >= 3 and parts[0] == "blogs":
        if parts[2] in {"tagged", "atom", "oembed"}:
            return None

        if any("${" in p or "}" in p for p in parts):
            return None

        return "blogs"

    return None


def local_page_exists(path):
    if path == "/":
        return (SITE / "index.html").exists()

    clean = path.strip("/")

    return (SITE / clean / "index.html").exists()


print("=" * 70)
print("CONTRÔLE DES LIENS V3")
print("=" * 70)

html_files = list(SITE.rglob("*.html"))
print(f"Pages HTML trouvées : {len(html_files):,}")

# Toutes les pages locales existantes
local_pages = set()

for f in html_files:
    rel = f.relative_to(SITE).as_posix()

    if rel == "index.html":
        local_pages.add("/")
    elif rel.endswith("/index.html"):
        local_pages.add("/" + rel[:-10])

print(f"Pages locales indexées : {len(local_pages):,}")

missing = Counter()
missing_examples = {}

stats = Counter()
total_links = 0

href_re = re.compile(
    r'''(?:href|data-href)\s*=\s*["']([^"']+)["']''',
    re.I
)

for i, html_file in enumerate(html_files, 1):

    try:
        text = html_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        stats["read_errors"] += 1
        continue

    # URL de base approximative correspondant à la page locale
    rel = html_file.relative_to(SITE).as_posix()

    if rel == "index.html":
        base_url = "https://ibuture.com/"
    else:
        directory = rel.rsplit("/", 1)[0]
        base_url = "https://ibuture.com/" + directory + "/"

    for href in href_re.findall(text):

        total_links += 1

        path = normalize_path(href, base_url)

        if not path:
            stats["ignored"] += 1
            continue

        if is_dynamic(path):
            stats["dynamic"] += 1
            continue

        if is_locale_path(path):
            stats["locale"] += 1
            continue

        suffix = Path(path).suffix.lower()

        if suffix in NON_HTML_EXT:
            stats["assets"] += 1
            continue

        page_type = classify_page(path)

        if not page_type:
            stats["other"] += 1
            continue

        if local_page_exists(path):
            stats[f"valid_{page_type}"] += 1
        else:
            stats[f"missing_{page_type}"] += 1
            missing[path] += 1

            if path not in missing_examples:
                missing_examples[path] = html_file.as_posix()

    if i % 500 == 0:
        print(f"[{i:,}/{len(html_files):,}] pages analysées")

print()
print("=" * 70)
print("RÉSULTAT")
print("=" * 70)

print(f"Liens <a> / data-href analysés : {total_links:,}")
print(f"Liens dynamiques Shopify       : {stats['dynamic']:,}")
print(f"Liens locales ignorés          : {stats['locale']:,}")
print(f"Assets / fichiers              : {stats['assets']:,}")
print(f"Autres liens                   : {stats['other']:,}")
print()

print("PAGES VALIDES")
print("-" * 70)

for t in ("products", "collections", "blogs", "pages", "root"):
    print(f"{t:15} : {stats[f'valid_{t}']:,}")

print()
print("PAGES RÉELLEMENT MANQUANTES")
print("-" * 70)

total_missing = 0

for t in ("products", "collections", "blogs", "pages"):
    n = stats[f"missing_{t}"]
    total_missing += n
    print(f"{t:15} : {n:,}")

print("-" * 70)
print(f"TOTAL UNIQUE    : {len(missing):,}")
print(f"TOTAL OCCURRENCES: {total_missing:,}")

# Résolution
candidate_links = (
    sum(stats[f"valid_{t}"] for t in ("products", "collections", "blogs", "pages"))
    + total_missing
)

if candidate_links:
    resolution = (
        sum(stats[f"valid_{t}"] for t in ("products", "collections", "blogs", "pages"))
        / candidate_links
        * 100
    )
else:
    resolution = 100

print(f"Taux de résolution : {resolution:.2f}%")

# Écriture des listes
all_file = Path("vraies_pages_manquantes_v3.txt")

with all_file.open("w", encoding="utf-8") as f:
    for path, count in missing.most_common():
        f.write(f"{count:6} {path}\n")

for page_type in ("products", "collections", "blogs", "pages"):

    outfile = Path(f"{page_type}_manquants_v3.txt")

    with outfile.open("w", encoding="utf-8") as f:

        paths = []

        for path in missing:
            if classify_page(path) == page_type:
                paths.append(path)

        for path in sorted(paths):
            f.write(path + "\n")

print()
print("FICHIERS CRÉÉS")
print("-" * 70)
print("vraies_pages_manquantes_v3.txt")
print("produits_manquants_v3.txt")
print("collections_manquantes_v3.txt")
print("blogs_manquants_v3.txt")
print("pages_manquants_v3.txt")

print()
print("TOP 50 DES PAGES MANQUANTES")
print("-" * 70)

for path, count in missing.most_common(50):
    print(f"{count:6}  {path}")

print()
print("=" * 70)
print("ANALYSE TERMINÉE")
print("=" * 70)
