from pathlib import Path
import re
import shutil
from datetime import datetime

FILE = Path("site/cdn/shop/t/52/assets/theme.js")

if not FILE.exists():
    raise SystemExit(f"Fichier introuvable : {FILE}")

# Sauvegarde
backup = FILE.with_name(
    FILE.name + ".backup-" + datetime.now().strftime("%Y%m%d-%H%M%S")
)
shutil.copy2(FILE, backup)

text = FILE.read_text(encoding="utf-8")

old_find = r'''_findWooVariation\(\)\{.*?\n\}
_syncSelectedVariant\(\)\{'''

new_find = '''_findWooVariation(){
if(!this._product?.variations?.length)return null;

const selectedId=String(window.qbkStore?.selectedId||"");

if(selectedId){
const variation=this._product.variations.find(variation=>
String(variation.shopify_variant_id||"")===selectedId
);

if(variation)return variation;
}

const selectedOptions=this._getSelectedOptions();

return this._product.variations.find(variation=>{
const attributes=variation.attributes||{};
const positions=Object.keys(selectedOptions);

return positions.length>0&&positions.every(position=>{
const wooValue=
attributes["option"+position] ??
attributes["attribute_option"+position] ??
"";

return String(wooValue).trim()===String(selectedOptions[position]).trim();
});
})||null;
}
_syncSelectedVariant(){'''

text2, count1 = re.subn(old_find, new_find, text, count=1, flags=re.S)

if count1 != 1:
    print("ERREUR : bloc _findWooVariation introuvable.")
    print(f"Sauvegarde conservée : {backup}")
    raise SystemExit(1)

old_option = r'''async _onOptionChanged\(event\)\{.*?\n\}
\};'''

new_option = '''async _onOptionChanged(event){
if(!event.target.matches("input[data-option-position]"))return;

const selectedOptions=this._getSelectedOptions();

const variation=this._product?.variations?.find(variation=>{
const attributes=variation.attributes||{};
const positions=Object.keys(selectedOptions);

return positions.length>0&&positions.every(position=>{
const wooValue=
attributes["option"+position] ??
attributes["attribute_option"+position] ??
"";

return String(wooValue).trim()===String(selectedOptions[position]).trim();
});
});

if(variation?.shopify_variant_id){
window.qbkStore.selectedId=String(variation.shopify_variant_id);
}

this._syncSelectedVariant();
}
};'''

text3, count2 = re.subn(old_option, new_option, text2, count=1, flags=re.S)

if count2 != 1:
    print("ERREUR : bloc _onOptionChanged introuvable.")
    print(f"Sauvegarde conservée : {backup}")
    raise SystemExit(1)

FILE.write_text(text3, encoding="utf-8")

print("==========================================")
print("CORRECTION APPLIQUÉE")
print("==========================================")
print(f"Fichier : {FILE}")
print(f"Backup  : {backup}")
print()
print("Méthodes corrigées :")
print("  - _findWooVariation()")
print("  - _onOptionChanged()")
print()
print("La recherche utilise maintenant directement")
print("shopify_variant_id présent dans les variations Woo.")
print("==========================================")
