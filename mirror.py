import os
import re
import time
import argparse
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

SKIP_PATHS = (
    "/cart", "/checkout", "/account", "/search",
    "/apps", "/admin", "/password", "/challenge"
)

ALLOWED_EXTERNAL_HOSTS = {
    "cdn.shopify.com",
    "cdn.shopifycdn.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
}

def clean_url(url):
    url, _ = urldefrag(url)
    return url

def is_allowed(url, base_host):
    p = urlparse(url)

    if p.scheme not in ("http", "https"):
        return False

    host = p.netloc.lower().split(":")[0]

    if host != base_host and host not in ALLOWED_EXTERNAL_HOSTS:
        return False

    if host == base_host:
        path = p.path.lower()

        if any(path.startswith(x) for x in SKIP_PATHS):
            return False

        # Évite les URLs avec trop de paramètres dynamiques
        if len(p.query) > 100:
            return False

    return True

def local_path(url, output):
    p = urlparse(url)
    path = p.path

    if not path or path == "/":
        return os.path.join(output, "index.html")

    # Ressources avec extension
    filename = os.path.basename(path)

    if "." in filename:
        return os.path.join(output, path.lstrip("/"))

    return os.path.join(output, path.lstrip("/"), "index.html")

def rewrite_url(original, current_url, output, base_host):
    if not original:
        return original

    absolute = clean_url(urljoin(current_url, original))
    p = urlparse(absolute)

    if p.scheme not in ("http", "https"):
        return original

    host = p.netloc.lower().split(":")[0]

    if host != base_host and host not in ALLOWED_EXTERNAL_HOSTS:
        return original

    target = local_path(absolute, output)

    current_file = local_path(current_url, output)

    try:
        rel = os.path.relpath(target, os.path.dirname(current_file))
        return rel.replace(os.sep, "/")
    except Exception:
        return original

def save_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "wb") as f:
        f.write(content)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--output", default="site")
    args = parser.parse_args()

    start_url = clean_url(args.url)
    base_host = urlparse(start_url).netloc.lower().split(":")[0]

    os.makedirs(args.output, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; WebsiteMirror/1.0)"
    })

    queue = deque([start_url])
    visited = set()
    downloaded = set()

    pages = 0
    assets = 0

    while queue and pages < args.max_pages:

        url = clean_url(queue.popleft())

        if url in visited:
            continue

        if not is_allowed(url, base_host):
            continue

        visited.add(url)

        print(f"[PAGE {pages + 1}] {url}")

        try:
            response = session.get(
                url,
                timeout=30,
                allow_redirects=True
            )

            if response.status_code != 200:
                print(f"  -> HTTP {response.status_code}")
                continue

        except Exception as e:
            print(f"  -> ERREUR: {e}")
            continue

        content_type = response.headers.get("content-type", "").lower()

        # HTML
        if "text/html" in content_type:

            soup = BeautifulSoup(response.text, "html.parser")

            # Découverte des pages
            for tag in soup.find_all(["a", "link"]):

                attr = "href"

                if not tag.get(attr):
                    continue

                absolute = clean_url(urljoin(url, tag[attr]))

                if is_allowed(absolute, base_host):
                    host = urlparse(absolute).netloc.lower().split(":")[0]

                    # On ne crawl que les pages du domaine principal
                    if host == base_host:
                        path = urlparse(absolute).path

                        if not any(path.lower().startswith(x) for x in SKIP_PATHS):
                            if absolute not in visited:
                                queue.append(absolute)

                tag[attr] = rewrite_url(
                    tag[attr],
                    url,
                    args.output,
                    base_host
                )

            # Images / scripts / styles / sources
            for tag, attr in [
                ("img", "src"),
                ("script", "src"),
                ("source", "src"),
                ("video", "src"),
                ("audio", "src"),
            ]:

                for element in soup.find_all(tag):

                    src = element.get(attr)

                    if not src:
                        continue

                    absolute = clean_url(urljoin(url, src))

                    if not is_allowed(absolute, base_host):
                        continue

                    try:
                        if absolute not in downloaded:

                            r = session.get(
                                absolute,
                                timeout=30
                            )

                            if r.status_code == 200:

                                path = local_path(
                                    absolute,
                                    args.output
                                )

                                save_file(path, r.content)

                                downloaded.add(absolute)
                                assets += 1

                                print(f"  [ASSET] {absolute}")

                        element[attr] = rewrite_url(
                            src,
                            url,
                            args.output,
                            base_host
                        )

                    except Exception as e:
                        print(f"  -> asset error: {e}")

            # CSS
            for element in soup.find_all("link"):

                href = element.get("href")

                if not href:
                    continue

                rel = " ".join(element.get("rel", [])).lower()

                if "stylesheet" not in rel:
                    continue

                absolute = clean_url(urljoin(url, href))

                if not is_allowed(absolute, base_host):
                    continue

                try:

                    if absolute not in downloaded:

                        r = session.get(
                            absolute,
                            timeout=30
                        )

                        if r.status_code == 200:

                            path = local_path(
                                absolute,
                                args.output
                            )

                            save_file(path, r.content)

                            downloaded.add(absolute)
                            assets += 1

                            print(f"  [CSS] {absolute}")

                    element["href"] = rewrite_url(
                        href,
                        url,
                        args.output,
                        base_host
                    )

                except Exception as e:
                    print(f"  -> CSS error: {e}")

            # Sauvegarde HTML
            path = local_path(url, args.output)

            save_file(
                path,
                soup.prettify().encode("utf-8")
            )

            pages += 1

        else:
            # Ressource non HTML
            path = local_path(url, args.output)

            save_file(path, response.content)

            assets += 1

        time.sleep(0.5)

    print()
    print("=" * 60)
    print("MIRROR TERMINÉ")
    print("=" * 60)
    print(f"Pages HTML : {pages}")
    print(f"Assets     : {assets}")
    print(f"Dossier    : {args.output}")
    print("=" * 60)

if __name__ == "__main__":
    main()
