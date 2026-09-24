import json
import shutil
from pathlib import Path
from urllib.parse import urlparse, unquote

BASE = Path("/workspaces/ibuture")
SITE = BASE / "site"
CATALOG = BASE / "products_catalog_v6.json"
OUT = BASE / "import_test"

LIMIT = 10

# Nettoyage du précédent test
if OUT.exists():
    shutil.rmtree(OUT)

(OUT / "images").mkdir(parents=True)

# Lecture catalogue
with open(CATALOG, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data["products"][:LIMIT]


def find_local_image(url):
    """Recherche une image du miroir à partir de son nom de fichier."""
    if not url:
        return None

    path = unquote(urlparse(url).path)
    basename = Path(path).name

    if not basename:
        return None

    matches = list(SITE.rglob(basename))

    matches = [
        p for p in matches
        if p.is_file()
        and p.suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".webp", ".gif"
        }
    ]

    if not matches:
        return None

    return matches[0]


result = []

print()
print("======================================")
print("   PREPARATION IMPORT TEST V8.1.1")
print("======================================")
print(f"Produits demandés : {len(products)}")
print()

total_images = 0
missing_images = 0

for number, product in enumerate(products, start=1):

    slug = product.get("slug", "")
    name = product.get("name", "")
    shopify = product.get("shopify", {})

    shopify_handle = shopify.get("handle", slug)
    shopify_id = shopify.get("id")

    p = dict(product)

    local_images = []

    for i, image_url in enumerate(product.get("images", []), start=1):

        local = find_local_image(image_url)

        if local:
            ext = local.suffix.lower()
            dest_name = f"{slug}__{i}{ext}"
            dest = OUT / "images" / dest_name

            shutil.copy2(local, dest)

            local_images.append({
                "source_url": image_url,
                "local_file": f"images/{dest_name}"
            })

            total_images += 1

        else:
            local_images.append({
                "source_url": image_url,
                "local_file": None
            })

            missing_images += 1

    p["import_images"] = local_images

    result.append(p)

    found = sum(
        1 for image in local_images
        if image.get("local_file")
    )

    missing = len(local_images) - found

    status = f"{found} image(s)"

    if missing:
        status += f" | {missing} ABSENTE(S)"

    print(
        f"{number:02d}. {name}"
    )
    print(
        f"    slug      : {slug}"
    )
    print(
        f"    Shopify   : {shopify_handle} | ID={shopify_id}"
    )
    print(
        f"    images    : {status}"
    )
    print()

# Sauvegarde du catalogue de test
with open(OUT / "products_test.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("--------------------------------------")
print(f"Produits préparés : {len(result)}")
print(f"Images trouvées   : {total_images}")
print(f"Images absentes   : {missing_images}")
print(f"Catalogue test    : {OUT / 'products_test.json'}")
print(f"Images test       : {OUT / 'images'}")
print("--------------------------------------")

# Taille du paquet
files = list(OUT.rglob("*"))
file_count = sum(1 for x in files if x.is_file())
size = sum(x.stat().st_size for x in files if x.is_file())

print(f"Fichiers générés  : {file_count}")
print(f"Taille du test    : {size / 1024 / 1024:.2f} MB")
print("======================================")
