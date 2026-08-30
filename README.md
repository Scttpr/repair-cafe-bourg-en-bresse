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
`jour`, `date`, `debut` et `fin`. **Ne les modifiez pas à la main**, ils sont
écrasés à chaque exécution — pour changer la date affichée, changez l'agenda.

Le lieu et l'adresse sont écrits en dur, sans `data-cal` : ils ne bougent pas
d'une séance à l'autre, et l'agenda ne peut pas les écraser. Le script sait les
remplir (clés `lieu` et `adresse`) si vous rajoutez un jour les attributs.

Le script gère les récurrences (`RRULE` hebdomadaires et mensuelles, y compris
« 2e samedi » et « dernier samedi »), les exceptions `EXDATE`, les séances
déplacées ou annulées, et ramène tout en heure de Paris — voir la note sur le
fuseau de l'agenda ci-dessous, qui demande un traitement particulier.

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
le titre, ce qui est fiable.

**2. Le fuseau de l'agenda est réglé sur UTC** (`X-WR-TIMEZONE:UTC`) au lieu
d'Europe/Paris. Les séances sont saisies en heure de Paris — 15h30 — mais
Google les exporte suffixées `Z`, donc étiquetées UTC. Prises au mot, elles
seraient affichées à 17h30 l'été et 16h30 l'hiver.

Le script s'en sort en **lisant l'heure telle qu'écrite** et en l'estampillant
Europe/Paris, sans conversion : 15h30 dans l'agenda donne 15h30 sur la page,
toute l'année. Ce contournement s'active tout seul quand le flux annonce
`X-WR-TIMEZONE:UTC`, et se désamorcera de lui-même le jour où l'agenda
repassera sur Europe/Paris.

Le corriger vraiment demande deux gestes, dans cet ordre : passer *Paramètres
→ Fuseau horaire* sur Europe/Paris, **puis** vérifier les horaires affichés —
Google conserve l'instant absolu des événements existants, ils se retrouveront
donc à 17h30 et devront être redescendus à 15h30. Tant que ce n'est pas fait,
laissez le contournement actif.

### Réglages du script

| Variable | Défaut | Rôle |
|---|---|---|
| `SEANCE_ICS_URL` | l'agenda de l'asso | flux `.ics` à lire |
| `SEANCE_FILTRE` | `permanence\|repair\|caf[eé]\|atelier` | regex sur le titre |
| `SEANCE_DUREE_MIN` | `180` | repli : durée minimale, en minutes |
| `SEANCE_HEURES_MURALES` | `auto` | `1` force la lecture murale, `0` la désactive, `auto` suit `X-WR-TIMEZONE` |

## Les champs à compléter à la main

Ils s'affichent en orange sur fond rose : impossible de les rater. Cherchez
`<span class="tbd">` dans `index.html`, remplacez le texte, puis supprimez la
classe `tbd` pour faire disparaître le surlignage.

| Placeholder | Ce qu'il faut mettre |
|---|---|
| `[EMAIL DE CONTACT]` | ⚠️ aussi dans 3 liens `mailto:` |
| `[NUMÉRO DE TÉLÉPHONE]` | ⚠️ aussi dans le lien `tel:` |
| `[LIEN FACEBOOK]` | ⚠️ aussi dans le `href` |
| `[NB]` ×3 | compteurs de la section Impact |
| `[ANNÉE]` | année de référence des compteurs |
| `[NOM DE L ASSOCIATION]` | raison sociale exacte, pied de page |

Les liens à corriger en même temps que le texte portent un commentaire `TODO`
juste au-dessus.

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
