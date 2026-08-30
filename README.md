# Repair Café Bourg-en-Bresse — page vitrine

Page statique d'une seule feuille, sans build ni dépendance. Elle reprend
l'identité visuelle du réseau international (`repaircafe.org`) : Roboto,
bleu-violet `#2d2e82`, corail `#ed6a42`, lavande `#e8e8ff`.

**En ligne :** https://scttpr.github.io/repair-cafe-bourg-en-bresse/

```
index.html                            la page (10 sections)
style.css                             tout le style, palette en variables CSS
.nojekyll                             sert le HTML tel quel sur Pages
scripts/prochaine_seance.py           lit l'agenda, remplit la date de séance
scripts/test_prochaine_seance.py      tests du parseur (hors ligne)
.github/workflows/prochaine-seance.yml  passe tous les jours à 04h17 UTC
```

## Prévisualiser en local

```bash
nix-shell -p python3 --run "python3 -m http.server 8000"
# puis http://localhost:8000
```

Un double-clic sur `index.html` fonctionne aussi.

## La date de séance se remplit toute seule

La section « Prochaine séance » est alimentée par l'agenda Google public de
l'association. Un workflow GitHub Actions lit le flux `.ics`, calcule la
prochaine occurrence à venir et réécrit la page ; le push sur `main` relance
la publication Pages dans la foulée.

```bash
python3 scripts/prochaine_seance.py --check   # affiche sans rien écrire
python3 scripts/prochaine_seance.py           # met index.html à jour
python3 scripts/test_prochaine_seance.py      # 19 tests, sans réseau
```

Les éléments concernés portent un attribut `data-cal` dans `index.html` :
`jour`, `date`, `debut`, `fin`, plus `lieu` et `adresse` si l'agenda expose le
champ « Lieu ». **Ne les modifiez pas à la main**, ils sont écrasés à chaque
exécution — pour changer la date affichée, changez l'agenda.

Le script gère les récurrences (`RRULE` hebdomadaires et mensuelles, y compris
« 2e samedi » et « dernier samedi »), les exceptions `EXDATE`, les séances
déplacées ou annulées, et convertit tout en heure de Paris.

### ⚠️ Deux réglages à corriger dans l'agenda

**1. Le partage est en mode « libre/occupé ».** Tous les événements sortent
sous le titre `Busy`, sans lieu ni description. Le script ne peut donc pas
distinguer une permanence d'une réunion de bureau : il se rabat sur le créneau
le plus long (seuil `SEANCE_DUREE_MIN`, 180 min par défaut) et affiche un
avertissement. **C'est une heuristique fragile** : si quelqu'un ajoute un long
événement à l'agenda, la page annoncera une date fausse sans prévenir.

Correctif : *Paramètres de l'agenda → Autorisations d'accès → Rendre disponible
publiquement → **Afficher tous les détails de l'événement***. Préfixez ensuite
les permanences par un mot-clé (`Permanence — …`) : le script filtre alors sur
le titre, ce qui est fiable, et récupère au passage le lieu et l'adresse.

**2. Le fuseau de l'agenda est réglé sur UTC** (`X-WR-TIMEZONE:UTC`) au lieu
d'Europe/Paris. Conséquence : le même créneau récurrent tombe à 17h30 en
septembre mais 16h30 en novembre, l'heure affichée bouge d'une heure à chaque
changement d'heure. À corriger dans *Paramètres → Fuseau horaire*.

### Réglages du script

| Variable | Défaut | Rôle |
|---|---|---|
| `SEANCE_ICS_URL` | l'agenda de l'asso | flux `.ics` à lire |
| `SEANCE_FILTRE` | `permanence\|repair\|caf[eé]\|atelier` | regex sur le titre |
| `SEANCE_DUREE_MIN` | `180` | repli : durée minimale, en minutes |

## Les champs à compléter à la main

Ils s'affichent en orange sur fond rose : impossible de les rater. Cherchez
`<span class="tbd">` dans `index.html`, remplacez le texte, puis supprimez la
classe `tbd` pour faire disparaître le surlignage.

| Placeholder | Ce qu'il faut mettre |
|---|---|
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

`[NOM DU LIEU]` et `[ADRESSE COMPLÈTE]` disparaîtront d'eux-mêmes le jour où
l'agenda exposera le champ « Lieu » (voir plus haut). Les liens à corriger en
même temps que le texte portent un commentaire `TODO` juste au-dessus.

Pour vérifier ce qu'il reste :

```bash
grep -c 'class="tbd"' index.html
```

## Publication

GitHub Pages est déjà branché sur `main` / `/ (root)` : **tout push sur `main`
republie le site** en une minute ou deux. Rien d'autre à faire.

## Logo

Le logotype est construit en CSS. Le logo officiel n'est pas repris ici :
« Repair Café » est une marque de la Stichting Repair Café International.
Si l'association est un affilié déclaré et dispose du fichier, il peut
remplacer le bloc `.logo` dans `index.html`.
