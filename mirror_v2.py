import os
import re
import time
import hashlib
import argparse
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse, unquote

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)

ALLOWED_HOSTS = {
    "ibuture.com",
    "www.ibuture.com",
    "cdn.shopify.com",
    "cdn.shopifycdn.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "shopifycloud.com",
}

SKIP_SEGMENTS = {
    "cart",
    "checkout",
    "account",
    "search",
    "apps",
    "admin",
    "challenge",
    "password",
}

ASSET_EXTENSIONS = {
    ".css", ".js", ".mjs",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".webm", ".mov",
    ".json", ".xml", ".txt"
}

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

visited_pages = set()
queued_pages = set()
downloaded_assets = set()

stats = {
    "pages_new": 0,
    "pages_existing": 0,
    "assets_new": 0,
    "assets_existing": 0,
    "errors": 0,
}


def normalize_url(url):
    p = urlparse(url)

    if p.scheme not in ("http", "https"):
        return None

    host = p.netloc.lower().split(":")[0]

    if host == "www.ibuture.com":
        host = "ibuture.com"

    # On garde les chemins, mais on supprime les paramètres
    # qui créent souvent des doublons dynamiques Shopify.
    path = p.path or "/"

    return urlunparse(("https", host, path, "", "", ""))


def host_allowed(url):
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
    except:
        return False

    if host in ("ibuture.com", "www.ibuture.com"):
        return True

    if host.endswith(".shopify.com"):
        return True

    if host.endswith(".shopifycdn.net"):
        return True

    if host.endswith(".shopifycloud.com"):
        return True

    if host in ("cdn.shopify.com", "cdn.shopifycdn.net"):
        return True

    if host in ("fonts.googleapis.com", "fonts.gstatic.com"):
        return True

    return False


def path_is_skipped(path):
    parts = [x.lower() for x in path.split("/") if x]

    for part in parts:
        if part in SKIP_SEGMENTS:
            return True

    return False


def is_page_url(url):
    p = urlparse(url)

    if p.netloc.lower().split(":")[0] not in (
        "ibuture.com",
        "www.ibuture.com",
    ):
        return False

    if path_is_skipped(p.path):
        return False

    # Pas de paramètres : on cherche les vraies pages.
    if p.query:
        return False

    return True


def safe_filename(path):
    path = unquote(path)

    if not path or path == "/":
        return "index.html"

    path = path.split("?")[0].split("#")[0]

    if path.endswith("/"):
        return path.lstrip("/") + "index.html"

    filename = os.path.basename(path)

    # Si aucune extension connue, considérer comme HTML
    ext = os.path.splitext(filename)[1].lower()

    if not ext:
        return path.lstrip("/") + "/index.html"

    return path.lstrip("/")


def local_path_for_url(url, output):
    p = urlparse(url)

    host = p.netloc.lower().split(":")[0]
    path = p.path or "/"

    if host in ("ibuture.com", "www.ibuture.com"):
        rel = safe_filename(path)
    else:
        # Conserver le domaine pour éviter les collisions.
        rel = os.path.join(
            host,
            path.lstrip("/")
        )

        if not os.path.splitext(rel)[1]:
            rel += ".bin"

    return os.path.join(output, rel)


def file_exists(url, output):
    return os.path.isfile(local_path_for_url(url, output))


def make_parent(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def save_response(url, response, output):
    path = local_path_for_url(url, output)
    make_parent(path)

    with open(path, "wb") as f:
        f.write(response.content)

    return path


def rewrite_url_in_html(original, page_url, output):
    if not original:
        return original

    original = original.strip()

    if (
        original.startswith("#")
        or original.startswith("data:")
        or original.startswith("mailto:")
        or original.startswith("tel:")
        or original.startswith("javascript:")
    ):
        return original

    absolute = urljoin(page_url, original)
    normalized = normalize_url(absolute)

    if not normalized or not host_allowed(normalized):
        return original

    if file_exists(normalized, output):
        local = local_path_for_url(normalized, output)
        page_local = local_path_for_url(page_url, output)

        try:
            return os.path.relpath(local, os.path.dirname(page_local)).replace(
                os.sep, "/"
            )
        except:
            return original

    return original


def download_asset(url, output):
    normalized = normalize_url(url)

    if not normalized or not host_allowed(normalized):
        return None

    if normalized in downloaded_assets:
        return local_path_for_url(normalized, output)

    downloaded_assets.add(normalized)

    path = local_path_for_url(normalized, output)

    if os.path.isfile(path):
        stats["assets_existing"] += 1
        return path

    try:
        r = session.get(normalized, timeout=30)

        if r.status_code != 200:
            stats["errors"] += 1
            return None

        save_response(normalized, r, output)
        stats["assets_new"] += 1

        time.sleep(0.15)

        return path

    except Exception:
        stats["errors"] += 1
        return None


def extract_css_urls(css):
    urls = set()

    # url(...)
    for match in re.findall(
        r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)",
        css,
        flags=re.I
    ):
        if not match.startswith("data:"):
            urls.add(match.strip())

    # @import
    for match in re.findall(
        r'@import\s+(?:url\()?["\']?([^"\')\s;]+)',
        css,
        flags=re.I
    ):
        urls.add(match.strip())

    return urls


def process_css(url, content, output):
    text = content.decode("utf-8", errors="ignore")

    for raw in extract_css_urls(text):
        absolute = urljoin(url, raw)
        normalized = normalize_url(absolute)

        if not normalized or not host_allowed(normalized):
            continue

        download_asset(normalized, output)

        local = local_path_for_url(normalized, output)
        current = local_path_for_url(url, output)

        try:
            relative = os.path.relpath(
                local,
                os.path.dirname(current)
            ).replace(os.sep, "/")

            text = text.replace(raw, relative)

        except:
            pass

    path = local_path_for_url(url, output)
    make_parent(path)

    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(text)


def process_html(url, content, output, queue):
    soup = BeautifulSoup(content, "html.parser")

    # Images
    for tag in soup.find_all(["img", "source"]):
        for attr in ["src", "data-src", "poster"]:
            value = tag.get(attr)

            if value:
                absolute = urljoin(url, value)
                normalized = normalize_url(absolute)

                if normalized and host_allowed(normalized):
                    download_asset(normalized, output)

                    local = local_path_for_url(normalized, output)

                    try:
                        page_local = local_path_for_url(url, output)
                        relative = os.path.relpath(
                            local,
                            os.path.dirname(page_local)
                        ).replace(os.sep, "/")

                        tag[attr] = relative
                    except:
                        pass

        # srcset
        srcset = tag.get("srcset")

        if srcset:
            new_items = []

            for item in srcset.split(","):
                parts = item.strip().split()

                if not parts:
                    continue

                raw = parts[0]
                absolute = urljoin(url, raw)
                normalized = normalize_url(absolute)

                if normalized and host_allowed(normalized):
                    download_asset(normalized, output)

                    local = local_path_for_url(normalized, output)

                    try:
                        page_local = local_path_for_url(url, output)
                        relative = os.path.relpath(
                            local,
                            os.path.dirname(page_local)
                        ).replace(os.sep, "/")

                        parts[0] = relative
                    except:
                        pass

                new_items.append(" ".join(parts))

            tag["srcset"] = ", ".join(new_items)

    # CSS
    for tag in soup.find_all("link"):
        href = tag.get("href")

        if href:
            absolute = urljoin(url, href)
            normalized = normalize_url(absolute)

            if normalized and host_allowed(normalized):
                local = download_asset(normalized, output)

                if local:
                    page_local = local_path_for_url(url, output)

                    try:
                        tag["href"] = os.path.relpath(
                            local,
                            os.path.dirname(page_local)
                        ).replace(os.sep, "/")
                    except:
                        pass

    # JS
    for tag in soup.find_all("script"):
        src = tag.get("src")

        if src:
            absolute = urljoin(url, src)
            normalized = normalize_url(absolute)

            if normalized and host_allowed(normalized):
                local = download_asset(normalized, output)

                if local:
                    page_local = local_path_for_url(url, output)

                    try:
                        tag["src"] = os.path.relpath(
                            local,
                            os.path.dirname(page_local)
                        ).replace(os.sep, "/")
                    except:
                        pass

    # Vidéos
    for tag in soup.find_all(["video", "source"]):
        src = tag.get("src")

        if src:
            absolute = urljoin(url, src)
            normalized = normalize_url(absolute)

            if normalized and host_allowed(normalized):
                download_asset(normalized, output)

    # Liens internes
    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        absolute = urljoin(url, href)
        normalized = normalize_url(absolute)

        if normalized and is_page_url(normalized):
            queue.append(normalized)
            queued_pages.add(normalized)

            # Réécriture uniquement si le fichier local existe.
            if file_exists(normalized, output):
                local = local_path_for_url(normalized, output)
                page_local = local_path_for_url(url, output)

                try:
                    tag["href"] = os.path.relpath(
                        local,
                        os.path.dirname(page_local)
                    ).replace(os.sep, "/")
                except:
                    pass

    path = local_path_for_url(url, output)
    make_parent(path)

    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(str(soup))


def crawl(start_url, output, max_pages):
    start_url = normalize_url(start_url)

    queue = deque([start_url])
    queued_pages.add(start_url)

    print("=" * 65)
    print("MIRROR V2 — REPRISE DU SITE EXISTANT")
    print("=" * 65)
    print(f"URL       : {start_url}")
    print(f"Dossier   : {output}")
    print(f"Maximum   : {max_pages} pages supplémentaires")
    print("IMPORTANT : aucun fichier existant ne sera supprimé.")
    print("=" * 65)

    while queue and stats["pages_new"] < max_pages:
        url = queue.popleft()

        if url in visited_pages:
            continue

        visited_pages.add(url)

        if not is_page_url(url):
            continue

        path = local_path_for_url(url, output)

        # Si déjà présent, on ne retélécharge pas la page.
        # Mais on la lit pour découvrir d'autres liens.
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    content = f.read()

                stats["pages_existing"] += 1

                process_html(url, content, output, queue)

                continue

            except Exception:
                pass

        try:
            print(
                f"[{stats['pages_new'] + 1}/{max_pages}] "
                f"{url}"
            )

            r = session.get(url, timeout=30)

            if r.status_code != 200:
                stats["errors"] += 1
                continue

            content_type = r.headers.get("content-type", "").lower()

            if "text/html" not in content_type:
                continue

            process_html(url, r.content, output, queue)

            stats["pages_new"] += 1

            time.sleep(0.5)

        except Exception as e:
            stats["errors"] += 1
            print("ERREUR :", e)

    print()
    print("=" * 65)
    print("CRAWL V2 TERMINÉ")
    print("=" * 65)
    print("Nouvelles pages       :", stats["pages_new"])
    print("Pages déjà présentes  :", stats["pages_existing"])
    print("Nouveaux assets       :", stats["assets_new"])
    print("Assets déjà présents  :", stats["assets_existing"])
    print("Erreurs               :", stats["errors"])
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--url",
        default="https://ibuture.com"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=3000
    )

    parser.add_argument(
        "--output",
        default="site"
    )

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    crawl(
        args.url,
        args.output,
        args.max_pages
    )
