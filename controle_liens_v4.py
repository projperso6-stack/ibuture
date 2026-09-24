import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup

SITE = Path("site")
BASE_URL = "https://ibuture.com"

# Extensions qui ne sont pas des pages HTML
NON_HTML_EXT = {
    ".atom", ".oembed", ".json", ".xml",
    ".js", ".css", ".map",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".avif", ".mp4", ".webm", ".mov",
    ".woff", ".woff2", ".ttf", ".otf",
    ".pdf", ".zip", ".txt", ".csv"
}

# Routes Shopify dynamiques / privées
DYNAMIC_PREFIXES = (
    "/cart",
    "/checkout",
    "/account",
    "/search",
    "/apps/",
    "/admin/",
    "/challenge",
    "/customer_authentication/",
)

# Préfixes de langues
LOCALE_RE = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$", re.I)


def normalize_path(path):
    """Normalise un chemin URL en chemin canonique."""
    path = unquote(path or "/")

    if not path.startswith("/"):
        path = "/" + path

    # Supprime les doubles slash
    path = re.sub(r"/{2,}", "/", path)

    # /index.html -> /
    if path.endswith("/index.html"):
        path = path[:-10]

    # /index/ -> /
    elif path.endswith("/index/"):
        path = path[:-6]

    if not path:
        path = "/"

    # Les chemins sans extension finissent par /
    last = path.rsplit("/", 1)[-1]

    if last and "." not in last and not path.endswith("/"):
        path += "/"

    return path


def remove_locale(path):
    """Supprime le premier segment de langue."""
    parts = path.strip("/").split("/")

    if parts and LOCALE_RE.match(parts[0]):
        parts = parts[1:]

    if not parts:
        return "/"

    return "/" + "/".join(parts) + ("/" if path.endswith("/") else "")


def is_locale_path(path):
    """Détecte une URL locale du type /fr-fr/... ou /de-de/..."""
    parts = path.strip("/").split("/")

    if not parts:
        return False

    return bool(LOCALE_RE.match(parts[0]))


def is_dynamic(path):
    """Détecte les routes Shopify dynamiques."""
    p = path.lower()

    for prefix in DYNAMIC_PREFIXES:
        if p.startswith(prefix):
            return True

    return False


def is_non_html(path):
    """Détecte les ressources ou endpoints qui ne sont pas des pages HTML."""
    p = path.lower()

    # Extensions
    last = p.rsplit("/", 1)[-1]

    for ext in NON_HTML_EXT:
        if last.endswith(ext):
            return True

    # Endpoints techniques
    technical = (
        "/feed",
        "/atom",
        "/oembed",
        "/tagged/",
        ".atom",
        ".oembed",
    )

    for x in technical:
        if x in p:
            return True

    # Listings génériques qui ne correspondent pas à une vraie page
    generic = {
        "/products/",
        "/collections/",
        "/pages/",
        "/blogs/",
        "/blogs/all/",
    }

    if p in generic:
        return True

    return False


def classify_page(path):
    """Classe une page statique."""
    p = remove_locale(path)
    parts = [x for x in p.strip("/").split("/") if x]

    if not parts:
        return "root"

    if parts[0] == "products" and len(parts) == 2:
        return "products"

    if parts[0] == "collections" and len(parts) == 2:
        return "collections"

    if parts[0] == "pages" and len(parts) == 2:
        return "pages"

    if parts[0] == "blogs" and len(parts) >= 3:
        if parts[1] == "all":
            return "blogs"

    return None


def build_local_index():
    """Construit l'index des pages HTML présentes localement."""
    pages = set()

    for f in SITE.rglob("index.html"):
        try:
            rel = f.parent.relative_to(SITE).as_posix()

            if rel == ".":
                path = "/"
            else:
                path = "/" + rel + "/"

            pages.add(normalize_path(path))

        except Exception:
            pass

    return pages


def source_url_from_file(file_path):
    """Transforme un fichier local en URL source approximative."""
    rel = file_path.parent.relative_to(SITE).as_posix()

    if rel == ".":
        return BASE_URL + "/"

    return BASE_URL + "/" + rel.strip("/") + "/"


def extract_links(html, source_url):
    """Extrait les href et data-href."""
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for tag in soup.find_all("a"):
        value = tag.get("href")
        if value:
            links.append(value)

    for tag in soup.find_all(attrs={"data-href": True}):
        value = tag.get("data-href")
        if value:
            links.append(value)

    return links


def canonicalize_target(raw, source_url):
    """Résout correctement les liens relatifs."""
    raw = (raw or "").strip()

    if not raw:
        return None

    # Ancres
    if raw.startswith("#"):
        return None

    # Javascript
    if raw.lower().startswith(("javascript:", "mailto:", "tel:", "sms:")):
        return None

    # URL complète / relative
    absolute = urljoin(source_url, raw)

    parsed = urlparse(absolute)

    # Seulement le domaine du site
    host = (parsed.netloc or "").lower()

    if host not in {
        "ibuture.com",
        "www.ibuture.com",
    }:
        return None

    path = normalize_path(parsed.path)

    return path


def main():
    print()
    print("=" * 70)
    print("CONTRÔLE DES LIENS V4")
    print("=" * 70)
    print()

    if not SITE.exists():
        print("ERREUR : dossier site/ introuvable.")
        return

    # ------------------------------------------------------------
    # 1. INDEX DES PAGES LOCALES
    # ------------------------------------------------------------
    print("[1] Construction de l'index local...")

    local_pages = build_local_index()

    print(f"Pages HTML trouvées : {len(local_pages):,}")
    print()

    # ------------------------------------------------------------
    # 2. STATISTIQUES
    # ------------------------------------------------------------
    total_links = 0
    internal_links = 0
    external_links = 0

    dynamic_links = 0
    locale_links = 0
    asset_links = 0
    other_links = 0

    valid_pages = 0
    missing_pages = 0

    valid_by_type = {
        "products": 0,
        "collections": 0,
        "blogs": 0,
        "pages": 0,
        "root": 0,
    }

    missing_by_type = {
        "products": 0,
        "collections": 0,
        "blogs": 0,
        "pages": 0,
        "root": 0,
    }

    missing_occurrences = {}

    relative_examples = []

    # ------------------------------------------------------------
    # 3. ANALYSE DES HTML
    # ------------------------------------------------------------
    html_files = list(SITE.rglob("index.html"))

    print("[2] Analyse des liens...")

    for i, file_path in enumerate(html_files, 1):

        try:
            html = file_path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            source_url = source_url_from_file(file_path)

            links = extract_links(html, source_url)

            for raw in links:

                total_links += 1

                raw_clean = raw.strip()

                # Exemple de lien relatif
                if (
                    not raw_clean.startswith(("http://", "https://", "//", "#"))
                    and len(relative_examples) < 20
                ):
                    relative_examples.append(
                        (source_url, raw_clean)
                    )

                # Résolution URL
                absolute = urljoin(source_url, raw_clean)
                parsed = urlparse(absolute)

                host = (parsed.netloc or "").lower()

                # ------------------------------------------------
                # EXTERNE
                # ------------------------------------------------
                if host and host not in {
                    "ibuture.com",
                    "www.ibuture.com",
                }:
                    external_links += 1
                    continue

                # ------------------------------------------------
                # LIEN LOCAL
                # ------------------------------------------------
                internal_links += 1

                path = normalize_path(parsed.path)

                # Dynamique
                if is_dynamic(path):
                    dynamic_links += 1
                    continue

                # Locale
                if is_locale_path(path):
                    locale_links += 1
                    continue

                # Asset / endpoint non HTML
                if is_non_html(path):
                    asset_links += 1
                    continue

                # Type de page
                page_type = classify_page(path)

                if page_type is None:
                    other_links += 1
                    continue

                # ------------------------------------------------
                # PAGE LOCALE EXISTANTE
                # ------------------------------------------------
                if path in local_pages:

                    valid_pages += 1
                    valid_by_type[page_type] += 1

                # ------------------------------------------------
                # PAGE MANQUANTE
                # ------------------------------------------------
                else:

                    missing_pages += 1
                    missing_by_type[page_type] += 1

                    key = path

                    if key not in missing_occurrences:
                        missing_occurrences[key] = 0

                    missing_occurrences[key] += 1

        except Exception as e:
            print()
            print(f"Erreur lecture : {file_path}")
            print(f"  {e}")

        # Progression tous les 500 fichiers
        if i % 500 == 0 or i == len(html_files):
            print(
                f"\r[{i:,}/{len(html_files):,}] "
                f"liens={total_links:,} "
                f"manquants={missing_pages:,}",
                end=""
            )

    print()
    print()

    # ------------------------------------------------------------
    # 4. RAPPORT
    # ------------------------------------------------------------
    print("=" * 70)
    print("RÉSULTATS")
    print("=" * 70)
    print()

    print(f"Pages HTML trouvées       : {len(local_pages):,}")
    print(f"Fichiers HTML analysés    : {len(html_files):,}")
    print()

    print(f"Liens <a>/data-href       : {total_links:,}")
    print(f"Liens internes            : {internal_links:,}")
    print(f"Liens externes            : {external_links:,}")
    print()

    print(f"Liens dynamiques Shopify  : {dynamic_links:,}")
    print(f"Liens locales ignorées    : {locale_links:,}")
    print(f"Assets / fichiers         : {asset_links:,}")
    print(f"Autres liens              : {other_links:,}")
    print()

    print("=" * 70)
    print("PAGES STATIQUES VALIDES")
    print("=" * 70)
    print()

    for key, value in valid_by_type.items():
        print(f"{key:<18}: {value:,}")

    print()

    print("=" * 70)
    print("PAGES RÉELLEMENT MANQUANTES")
    print("=" * 70)
    print()

    for key, value in missing_by_type.items():
        print(f"{key:<18}: {value:,}")

    print()

    print(f"TOTAL UNIQUE             : {len(missing_occurrences):,}")
    print(f"TOTAL OCCURRENCES        : {missing_pages:,}")

    if internal_links:
        resolved = valid_pages + dynamic_links + locale_links + asset_links + other_links

        taux_global = resolved / internal_links * 100

        print(f"Taux de résolution global: {taux_global:.2f}%")

    if valid_pages + missing_pages:
        taux_pages = valid_pages / (valid_pages + missing_pages) * 100

        print(f"Taux de résolution pages : {taux_pages:.2f}%")

    print()

    # ------------------------------------------------------------
    # 5. TOP DES VRAIES PAGES MANQUANTES
    # ------------------------------------------------------------
    if missing_occurrences:

        print("=" * 70)
        print("TOP 50 DES PAGES MANQUANTES")
        print("=" * 70)
        print()

        sorted_missing = sorted(
            missing_occurrences.items(),
            key=lambda x: (-x[1], x[0])
        )

        for path, count in sorted_missing[:50]:
            print(f"{count:>6}  {path}")

        print()

    else:
        print("=" * 70)
        print("AUCUNE PAGE STATIQUE MANQUANTE")
        print("=" * 70)
        print()

    # ------------------------------------------------------------
    # 6. EXEMPLES DE LIENS RELATIFS
    # ------------------------------------------------------------
    if relative_examples:

        print("=" * 70)
        print("EXEMPLES DE LIENS RELATIFS RÉSOLUS")
        print("=" * 70)
        print()

        for source, raw in relative_examples:
            target = canonicalize_target(raw, source)

            print(f"SOURCE : {source}")
            print(f"LIEN   : {raw}")
            print(f"TARGET : {target}")
            print()

    # ------------------------------------------------------------
    # 7. FIN
    # ------------------------------------------------------------
    print("=" * 70)
    print("CONTRÔLE TERMINÉ")
    print("=" * 70)
    print()
    print("Aucun fichier n'a été téléchargé.")
    print("Aucun fichier n'a été modifié.")
    print("Aucun fichier n'a été supprimé.")
    print()


if __name__ == "__main__":
    main()
