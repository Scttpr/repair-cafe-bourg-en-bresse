# Repair Café Bourg-en-Bresse — page vitrine

Page statique d'une seule feuille, sans build ni dépendance. Elle reprend
l'identité visuelle du réseau international (`repaircafe.org`) : Roboto,
bleu-violet `#2d2e82`, corail `#ed6a42`, lavande `#e8e8ff`.

```
index.html   la page (10 sections)
style.css    tout le style, palette en variables CSS dans :root
.nojekyll    demande à GitHub Pages de servir le HTML tel quel
```

## Prévisualiser en local

```bash
nix-shell -p python3 --run "python3 -m http.server 8000"
# puis http://localhost:8000
```

Un double-clic sur `index.html` fonctionne aussi.

## ⚠️ À FAIRE AVANT DE PUBLIER

La page contient **14 informations à compléter**. Elles s'affichent en orange
sur fond rose avec un soulignement pointillé : impossible de les rater.

Cherchez `<span class="tbd">` dans `index.html`, remplacez le texte, puis
supprimez la classe `tbd` pour faire disparaître le surlignage.

| Placeholder | Ce qu'il faut mettre |
|---|---|
| `[JOUR DE LA SEMAINE]` | ex. samedi |
| `[DATE DE LA PROCHAINE SÉANCE]` | ex. 12 octobre 2026 |
| `[HEURE DE DÉBUT]` / `[HEURE DE FIN]` | ex. 14h00 / 17h00 |
| `[PÉRIODICITÉ]` | ex. tous les 2e samedis du mois |
| `[NOM DU LIEU]` | ex. Centre social des Vennes |
| `[ADRESSE COMPLÈTE]` | rue, code postal, ville |
| `[ACCÈS ET STATIONNEMENT]` | bus, parking, accessibilité PMR |
| `[EMAIL DE CONTACT]` | ⚠️ aussi dans 3 liens `mailto:` |
| `[NUMÉRO DE TÉLÉPHONE]` | ⚠️ aussi dans le lien `tel:` |
| `[LIEN FACEBOOK]` | ⚠️ aussi dans le `href` |
| `[NB]` ×3 | compteurs de la section Impact |
| `[ANNÉE]` | année de référence des compteurs |
| `[NOM DE L ASSOCIATION]` | raison sociale exacte, pied de page |

Les liens à corriger en même temps que le texte portent un commentaire `TODO`
juste au-dessus. Pour vérifier qu'il n'en reste aucun :

```bash
grep -o '\[[A-ZÀ-ÜÉÈÊ0-9 ]*\]' index.html | sort -u
```

Quand cette commande ne renvoie plus rien (hors check-list en commentaire),
la page est prête.

## Mettre en ligne sur GitHub Pages

1. Créer un dépôt **public** sur github.com (Pages est réservé aux dépôts
   publics sur les comptes gratuits). Ne cochez ni README ni .gitignore :
   ce dépôt local en a déjà.
2. Relier et pousser :
   ```bash
   git remote add origin https://github.com/VOTRE-PSEUDO/NOM-DU-DEPOT.git
   git push -u origin main
   ```
3. Dans le dépôt : **Settings → Pages → Source : Deploy from a branch**,
   branche `main`, dossier `/ (root)`, puis **Save**.
4. Au bout d'une minute ou deux, le site est sur
   `https://VOTRE-PSEUDO.github.io/NOM-DU-DEPOT/`.

**Ne faites l'étape 3 qu'une fois les 14 champs remplis** : une page publiée
est indexée par les moteurs de recherche, et un cache Google se retire
beaucoup moins facilement qu'un dépôt.

## Logo

Le logotype est construit en CSS. Le logo officiel n'est pas repris ici :
« Repair Café » est une marque de la Stichting Repair Café International.
Si l'association est un affilié déclaré et dispose du fichier, il peut
remplacer le bloc `.logo` dans `index.html`.
