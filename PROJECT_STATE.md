# IBUTURE — État du projet

## Projet

Site de référence : https://ibuture.com

Repository GitHub :
https://github.com/wiliscko01/ibuture

Workspace :
/workspaces/ibuture

## Miroir

Le miroir complet du site se trouve dans :

/workspaces/ibuture/site/

Taille approximative actuelle : 7,3 Go.

IMPORTANT :
Le dossier `site/` est volontairement exclu de Git.
Il sert de copie de référence locale et ne doit pas être envoyé sur GitHub.

## État du miroir

Pages HTML présentes : environ 8 012.

Produits : environ 6 694.

Collections : environ 385.

Blogs : environ 56.

Pages : environ 816.

Le miroir contient la version de référence téléchargée et nettoyée.

## Nettoyage

Les blocs inutiles suivants ont été supprimés du HTML :

- LangShopConfig
- wpmLoader
- Shortly
- JudgeMe

Le nettoyage a permis de récupérer environ 1,4 Go.

Les données importantes des produits ont été conservées :

- prix
- variantes
- images
- descriptions
- données JSON
- JSON-LD
- informations produit

## Vérification

Le contrôle final a confirmé la présence des principales données produit.

Le contrôle des liens a été amélioré avec résolution correcte des URLs relatives.

Les liens statiques de la version de référence ont été vérifiés.

Les deux liens produits restants considérés comme manquants correspondent à des anciennes/variantes d'URL et ne nécessitent pas de téléchargement supplémentaire.

## Langues

Le site original possède de nombreuses variantes linguistiques.

Pour éviter de multiplier inutilement la taille du miroir, une seule version de référence a été téléchargée pour le moment.

Les autres langues seront téléchargées ultérieurement si nécessaire, puis pourront être intégrées dans le projet final via une stratégie multilingue adaptée.

## Scripts

Les scripts Python présents à la racine servent notamment à :

- télécharger le miroir
- analyser les sitemaps
- identifier les pages manquantes
- nettoyer le HTML
- vérifier le contenu
- contrôler les liens
- télécharger la version de référence
- préparer les prochaines versions linguistiques

## Architecture finale envisagée

Le miroir actuel est une référence visuelle et fonctionnelle.

Il ne constitue pas le back-office final.

Architecture envisagée :

Frontend / thème personnalisé
        ↓
WordPress
        ↓
WooCommerce
        ↓
Base de données

Fonctionnalités prévues :

- catalogue produits
- catégories
- recherche
- panier
- commande
- comptes clients
- gestion des stocks
- paiements
- livraison
- coupons
- commandes
- espace administrateur
- multilingue
- SEO
- emails transactionnels

## Prochaine grande étape

Concevoir l'architecture WordPress + WooCommerce avant de commencer l'intégration du catalogue.

Le miroir `site/` doit rester intact pendant cette phase.

## Règle importante

Ne jamais exécuter :

rm -rf site

ou

git add .

Le dossier `site/` ne doit pas être versionné sur GitHub.

Les scripts et documents du projet doivent être versionnés séparément du miroir.
