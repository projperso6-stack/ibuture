import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from html import unescape
from collections import Counter, defaultdict

SITE = Path("site")
DOMAIN = "ibuture.com"
BASE_URL = f"https://{DOMAIN}"

# Shopify / URLs dynamiques qui ne doivent pas être considérées
# comme des pages statiques manquantes.
DYNAMIC_PREFIXES = (
    "/cart",
    "/checkout",
    "/account",
    "/search",
    "/apps",
    "/admin",
    "/challenge",
    "/password",
    "/customer_authentication",
)

# Extensions qui ne représentent normalement pas des pages HTML.
NON_HTML_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".ico", ".avif", ".bmp",
    ".css", ".js", ".json",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".webm", ".mov", ".avi",
    ".pdf", ".zip", ".rar",
    ".xml", ".txt",
}

HTML_RE = re.compile(
    r'href\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE
)


def normalize_path(path):
    """
    Transforme une URL de page en chemin canonique du mirror.

    /foo       -> /foo/
    /foo/      -> /foo/
    /foo/index.html -> /foo/
    /          -> /
    """
    path = unquote(path)
    path = path.split("#", 1)[0]

    if not path:
        return "/"

    if path == "/index.html":
        return "/"

    if path.endswith("/index.html"):
        path = path[:-len("index.html")]

    if not path.startswith("/"):
        path = "/" + path

    # Nettoyage des doubles slash
    path = re.sub(r"/+", "/", path)

    # Les pages du mirror sont des dossiers avec index.html
    last = path.rsplit("/", 1)[-1]

    if last and "." not in last and not path.endswith("/"):
        path += "/"

    return path


def local_page_url(index_file):
    """
    Convertit :
        site/index.html
        site/products/foo/index.html
    en :
        /
        /products/foo/
    """
    rel = index_file.relative_to(SITE).as_posix()

    if rel == "index.html":
        return "/"

    if rel.endswith("/index.html"):
        return "/" + rel[:-len("index.html")]

    return "/" + rel


def is_locale_path(path):
    """
    Détecte les préfixes du type :
        /fr/
        /de/
        /it/
        /fr-nl/
        /de-at/
        /en-it/
    """
    parts = path.strip("/").split("/")

    if not parts or not parts[0]:
        return False

    first = parts[0].lower()

    return bool(
        re.fullmatch(r"[a-z]{2}", first)
        or re.fullmatch(r"[a-z]{2}-[a-z]{2}", first)
    )


def is_dynamic(path):
    path = path.lower()

    if path == "/":
        return False

    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in DYNAMIC_PREFIXES
    )


def looks_like_non_html(path):
    filename = path.rstrip("/").rsplit("/", 1)[-1]

    if "." not in filename:
        return False

    ext = "." + filename.rsplit(".", 1)[-1].lower()

    return ext in NON_HTML_EXTENSIONS


# ---------------------------------------------------------
# 1. INVENTAIRE DES PAGES LOCALES
# ---------------------------------------------------------

print()
print("=" * 70)
print("CONTRÔLE DES LIENS V2")
print("=" * 70)
print()

local_pages = set()

for index_file in SITE.rglob("index.html"):
    local_pages.add(
        normalize_path(local_page_url(index_file))
    )

print(f"Pages locales trouvées : {len(local_pages):,}")
print()


# ---------------------------------------------------------
# 2. ANALYSE
# ---------------------------------------------------------

total_links = 0
internal_links = 0
external_links = 0

valid_links = 0
dynamic_links = 0
locale_links = 0
non_html_links = 0

missing_links = 0

missing_counter = Counter()
missing_sources = defaultdict(list)

external_domains = Counter()

relative_links = 0
relative_resolved = 0


for index_file in SITE.rglob("index.html"):

    source_path = normalize_path(local_page_url(index_file))
    source_url = urljoin(BASE_URL + "/", source_path.lstrip("/"))

    try:
        html = index_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        continue

    for raw_href in HTML_RE.findall(html):

        total_links += 1

        href = unescape(raw_href.strip())

        if not href:
            continue

        # -------------------------------------------------
        # Ancres, javascript, mailto, tel...
        # -------------------------------------------------

        if href.startswith("#"):
            continue

        if href.lower().startswith((
            "javascript:",
            "mailto:",
            "tel:",
            "data:",
            "blob:"
        )):
            continue

        # -------------------------------------------------
        # Détection des liens relatifs
        # -------------------------------------------------

        parsed_raw = urlparse(href)

        if not parsed_raw.scheme and not href.startswith("//"):
            relative_links += 1

        # -------------------------------------------------
        # Résolution comme le ferait réellement le navigateur
        # -------------------------------------------------

        absolute = urljoin(source_url, href)

        parsed = urlparse(absolute)

        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()

        # -------------------------------------------------
        # Externe
        # -------------------------------------------------

        if hostname and hostname not in {
            DOMAIN,
            f"www.{DOMAIN}",
        }:

            external_links += 1

            if hostname:
                external_domains[hostname] += 1

            continue

        # Protocoles non HTTP
        if scheme not in ("http", "https"):
            continue

        internal_links += 1

        path = normalize_path(parsed.path)

        if not path:
            path = "/"

        # -------------------------------------------------
        # Liens dynamiques Shopify
        # -------------------------------------------------

        if is_dynamic(path):
            dynamic_links += 1
            continue

        # -------------------------------------------------
        # Assets / fichiers non HTML
        # -------------------------------------------------

        if looks_like_non_html(path):
            non_html_links += 1
            continue

        # -------------------------------------------------
        # Locale abandonnée
        # -------------------------------------------------

        if is_locale_path(path):
            locale_links += 1
            continue

        # -------------------------------------------------
        # Page locale existante
        # -------------------------------------------------

        if path in local_pages:
            valid_links += 1

            if not parsed_raw.scheme and not href.startswith("//"):
                relative_resolved += 1

            continue

        # -------------------------------------------------
        # PAGE STATIQUE RÉELLEMENT MANQUANTE
        # -------------------------------------------------

        missing_links += 1
        missing_counter[path] += 1

        if len(missing_sources[path]) < 5:
            missing_sources[path].append(source_path)


# ---------------------------------------------------------
# 3. RAPPORT
# ---------------------------------------------------------

print("=" * 70)
print("RÉSULTATS")
print("=" * 70)
print()

print(f"Liens <a> analysés       : {total_links:,}")
print(f"Liens internes           : {internal_links:,}")
print(f"Liens externes           : {external_links:,}")
print()

print(f"Liens internes valides   : {valid_links:,}")
print(f"Liens dynamiques Shopify : {dynamic_links:,}")
print(f"Liens locales abandonnées: {locale_links:,}")
print(f"Assets / non HTML        : {non_html_links:,}")
print(f"Pages réellement absentes: {missing_links:,}")
print()

static_candidates = (
    valid_links +
    missing_links
)

if static_candidates:
    resolution = (
        valid_links /
        static_candidates *
        100
    )
else:
    resolution = 100

print(
    f"Taux de résolution pages statiques : "
    f"{resolution:.2f}%"
)

print()

print(
    f"Liens relatifs correctement résolus : "
    f"{relative_resolved:,}"
)

print()


# ---------------------------------------------------------
# 4. TOP DES VRAIES PAGES MANQUANTES
# ---------------------------------------------------------

print("=" * 70)
print("TOP DES PAGES STATIQUES RÉELLEMENT MANQUANTES")
print("=" * 70)
print()

if not missing_counter:

    print("Aucune page statique manquante détectée.")
    print()

else:

    for i, (path, count) in enumerate(
        missing_counter.most_common(50),
        1
    ):

        print(f"{i:02d}. {path}")
        print(f"    occurrences : {count:,}")

        sources = missing_sources[path]

        if sources:
            print(
                f"    source      : "
                f"{sources[0]}"
            )

        print()


# ---------------------------------------------------------
# 5. SAUVEGARDE DES PAGES MANQUANTES
# ---------------------------------------------------------

missing_file = Path("liens_manquants_v2.txt")

with missing_file.open(
    "w",
    encoding="utf-8"
) as f:

    for path, count in missing_counter.most_common():

        f.write(
            f"{count:6d}  {path}\n"
        )


# ---------------------------------------------------------
# 6. DOMAINES EXTERNES
# ---------------------------------------------------------

print("=" * 70)
print("PRINCIPAUX DOMAINES EXTERNES")
print("=" * 70)
print()

for domain, count in external_domains.most_common(20):

    print(
        f"{domain:45s} {count:,}"
    )

print()

print("=" * 70)
print("FIN DU CONTRÔLE")
print("=" * 70)
print()

print(
    f"Liste détaillée sauvegardée dans : "
    f"{missing_file}"
)

print()
