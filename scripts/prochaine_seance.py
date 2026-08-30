#!/usr/bin/env python3
"""Ecrit la prochaine seance du Repair Cafe dans index.html.

Lit le flux iCalendar public de l'agenda Google, developpe les recurrences,
retient la prochaine occurrence a venir et remplit les elements marques
data-cal="..." dans la page. Aucune dependance : stdlib uniquement.

    python3 scripts/prochaine_seance.py            # met la page a jour
    python3 scripts/prochaine_seance.py --check    # affiche sans rien ecrire

Variables d'environnement :
    SEANCE_ICS_URL      flux .ics a lire
    SEANCE_FILTRE       regex sur le titre pour reconnaitre une permanence
    SEANCE_DUREE_MIN    repli : duree minimale en minutes (voir plus bas)
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ICS_URL = os.environ.get(
    "SEANCE_ICS_URL",
    "https://calendar.google.com/calendar/ical/"
    "repair.cafe.bourgenbresse%40gmail.com/public/basic.ics",
)

# Un titre qui matche = une permanence. Tant que l'agenda est partage en mode
# « libre/occupe », tous les titres valent « Busy » et rien ne matche : on
# bascule alors sur le repli par duree, ci-dessous.
FILTRE = re.compile(os.environ.get("SEANCE_FILTRE", r"permanence|repair|caf[eé]|atelier"), re.I)

# Repli utilise uniquement si aucun titre ne matche. L'agenda melange des
# creneaux de 4h30/5h30 (les permanences) et de 1h30 (autre chose) : le seuil
# ecarte les seconds. Heuristique fragile, d'ou l'avertissement emis.
DUREE_MIN = timedelta(minutes=int(os.environ.get("SEANCE_DUREE_MIN", "180")))

PARIS = ZoneInfo("Europe/Paris")
HORIZON = timedelta(days=730)
MAX_OCCURRENCES = 500

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
JOUR_ICS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


# --------------------------------------------------------------- lecture ICS

def deplier(texte: str) -> list[str]:
    """RFC 5545 : une ligne commencant par un espace prolonge la precedente."""
    lignes: list[str] = []
    for brute in texte.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if brute[:1] in (" ", "\t") and lignes:
            lignes[-1] += brute[1:]
        else:
            lignes.append(brute)
    return lignes


def decouper(ligne: str) -> tuple[str, dict[str, str], str] | None:
    """« DTSTART;TZID=Europe/Paris:20260905T173000 » -> (nom, params, valeur)."""
    sep = ligne.find(":")
    if sep == -1:
        return None
    entete, valeur = ligne[:sep], ligne[sep + 1 :]
    morceaux = entete.split(";")
    params = {}
    for p in morceaux[1:]:
        if "=" in p:
            cle, _, val = p.partition("=")
            params[cle.upper()] = val.strip('"')
    return morceaux[0].upper(), params, valeur


def echapper(valeur: str) -> str:
    r"""Deséchappe le texte iCalendar (\\, ;, \n ...)."""
    return (
        valeur.replace("\\\\", "\x00")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\N", "\n")
        .replace("\\n", "\n")
        .replace("\x00", "\\")
    ).strip()


def lire_date(valeur: str, params: dict[str, str]):
    """Rend un datetime aware, ou un date pour un evenement « journee entiere »."""
    valeur = valeur.strip()
    if params.get("VALUE") == "DATE" or (len(valeur) == 8 and "T" not in valeur):
        return date(int(valeur[0:4]), int(valeur[4:6]), int(valeur[6:8]))
    brut = datetime.strptime(valeur.rstrip("Z"), "%Y%m%dT%H%M%S")
    if valeur.endswith("Z"):
        return brut.replace(tzinfo=ZoneInfo("UTC")).astimezone(PARIS)
    tzid = params.get("TZID")
    try:
        fuseau = ZoneInfo(tzid) if tzid else PARIS
    except Exception:
        fuseau = PARIS
    return brut.replace(tzinfo=fuseau).astimezone(PARIS)


def en_datetime(valeur):
    """Normalise une date « journee entiere » en datetime a minuit."""
    if isinstance(valeur, datetime):
        return valeur
    return datetime(valeur.year, valeur.month, valeur.day, tzinfo=PARIS)


@dataclass
class Evenement:
    debut: datetime
    fin: datetime
    titre: str = ""
    lieu: str = ""
    journee: bool = False
    rrule: str = ""
    exdates: list = None
    uid: str = ""
    recurrence_id: object = None
    annule: bool = False

    @property
    def duree(self) -> timedelta:
        return self.fin - self.debut


def parser(texte: str) -> list[Evenement]:
    evenements: list[Evenement] = []
    courant: dict | None = None
    for ligne in deplier(texte):
        if ligne == "BEGIN:VEVENT":
            courant = {"exdates": []}
            continue
        if ligne == "END:VEVENT":
            if courant and "debut" in courant:
                debut = courant["debut"]
                journee = not isinstance(debut, datetime)
                fin = courant.get("fin") or debut
                evenements.append(
                    Evenement(
                        debut=en_datetime(debut),
                        fin=en_datetime(fin),
                        titre=courant.get("titre", ""),
                        lieu=courant.get("lieu", ""),
                        journee=journee,
                        rrule=courant.get("rrule", ""),
                        exdates=courant["exdates"],
                        uid=courant.get("uid", ""),
                        recurrence_id=courant.get("recurrence_id"),
                        annule=courant.get("statut", "") == "CANCELLED",
                    )
                )
            courant = None
            continue
        if courant is None:
            continue
        decoupe = decouper(ligne)
        if not decoupe:
            continue
        nom, params, valeur = decoupe
        if nom == "DTSTART":
            courant["debut"] = lire_date(valeur, params)
        elif nom == "DTEND":
            courant["fin"] = lire_date(valeur, params)
        elif nom == "SUMMARY":
            courant["titre"] = echapper(valeur)
        elif nom == "LOCATION":
            courant["lieu"] = echapper(valeur)
        elif nom == "RRULE":
            courant["rrule"] = valeur
        elif nom == "UID":
            courant["uid"] = valeur.strip()
        elif nom == "STATUS":
            courant["statut"] = valeur.strip().upper()
        elif nom == "RECURRENCE-ID":
            courant["recurrence_id"] = en_datetime(lire_date(valeur, params))
        elif nom == "EXDATE":
            for morceau in valeur.split(","):
                if morceau.strip():
                    courant["exdates"].append(en_datetime(lire_date(morceau, params)))
    return evenements


# ------------------------------------------------------- recurrences (RRULE)

def _nieme_jour(annee: int, mois: int, jour_semaine: int, rang: int) -> date | None:
    """rang=2 -> 2e <jour> du mois ; rang=-1 -> dernier."""
    premier = date(annee, mois, 1)
    suivant = date(annee + (mois == 12), (mois % 12) + 1, 1)
    jours = []
    curseur = premier
    while curseur < suivant:
        if curseur.weekday() == jour_semaine:
            jours.append(curseur)
        curseur += timedelta(days=1)
    if not jours:
        return None
    index = rang - 1 if rang > 0 else len(jours) + rang
    return jours[index] if 0 <= index < len(jours) else None


def developper(ev: Evenement, fin_horizon: datetime) -> list[datetime]:
    """Developpe la RRULE en une liste de dates de debut."""
    if not ev.rrule:
        return [ev.debut]

    regles = {}
    for part in ev.rrule.split(";"):
        if "=" in part:
            cle, _, val = part.partition("=")
            regles[cle.upper()] = val.upper()

    freq = regles.get("FREQ", "")
    intervalle = int(regles.get("INTERVAL", "1") or 1)
    compte = int(regles["COUNT"]) if "COUNT" in regles else None
    limite = fin_horizon
    if "UNTIL" in regles:
        try:
            limite = min(limite, en_datetime(lire_date(regles["UNTIL"], {})))
        except Exception:
            pass

    bydays = [j for j in regles.get("BYDAY", "").split(",") if j]
    exclus = {d.replace(tzinfo=None) for d in (ev.exdates or [])}
    debuts: list[datetime] = []

    def ajouter(moment: datetime) -> bool:
        """Rend False quand il faut arreter le developpement."""
        if moment > limite:
            return False
        if moment >= ev.debut and moment.replace(tzinfo=None) not in exclus:
            debuts.append(moment)
        return not (compte and len(debuts) >= compte)

    heure = ev.debut

    if freq in ("DAILY", "WEEKLY"):
        pas = timedelta(days=intervalle) if freq == "DAILY" else timedelta(weeks=intervalle)
        jours_cibles = [JOUR_ICS[j[-2:]] for j in bydays if j[-2:] in JOUR_ICS]
        semaine = ev.debut - timedelta(days=ev.debut.weekday())
        curseur = ev.debut if freq == "DAILY" or not jours_cibles else semaine
        for _ in range(MAX_OCCURRENCES):
            if curseur > limite:
                break
            if freq == "WEEKLY" and jours_cibles:
                for cible in sorted(jours_cibles):
                    moment = (curseur + timedelta(days=cible)).replace(
                        hour=heure.hour, minute=heure.minute, second=0, microsecond=0
                    )
                    if not ajouter(moment):
                        break
            else:
                if not ajouter(curseur):
                    break
            curseur += pas

    elif freq in ("MONTHLY", "YEARLY"):
        bymonthday = [int(x) for x in regles.get("BYMONTHDAY", "").split(",") if x.strip().lstrip("-").isdigit()]
        annee, mois = ev.debut.year, ev.debut.month
        for _ in range(MAX_OCCURRENCES):
            candidats: list[date] = []
            if bydays:
                for entree in bydays:
                    correspondance = re.match(r"^(-?\d+)?([A-Z]{2})$", entree)
                    if not correspondance:
                        continue
                    rang, code = correspondance.groups()
                    if code not in JOUR_ICS:
                        continue
                    if rang:
                        trouve = _nieme_jour(annee, mois, JOUR_ICS[code], int(rang))
                        if trouve:
                            candidats.append(trouve)
                    else:
                        jour = date(annee, mois, 1)
                        while jour.month == mois:
                            if jour.weekday() == JOUR_ICS[code]:
                                candidats.append(jour)
                            jour += timedelta(days=1)
            elif bymonthday:
                for numero in bymonthday:
                    try:
                        if numero > 0:
                            candidats.append(date(annee, mois, numero))
                        else:
                            fin_mois = date(annee + (mois == 12), (mois % 12) + 1, 1) - timedelta(days=1)
                            candidats.append(fin_mois + timedelta(days=numero + 1))
                    except ValueError:
                        pass
            else:
                try:
                    candidats.append(date(annee, mois, ev.debut.day))
                except ValueError:
                    pass

            arret = False
            for jour in sorted(candidats):
                moment = datetime(
                    jour.year, jour.month, jour.day,
                    heure.hour, heure.minute, tzinfo=PARIS,
                )
                if not ajouter(moment):
                    arret = True
                    break
            if arret:
                break
            saut = intervalle * (12 if freq == "YEARLY" else 1)
            mois += saut
            annee += (mois - 1) // 12
            mois = (mois - 1) % 12 + 1
            if datetime(annee, mois, 1, tzinfo=PARIS) > limite:
                break
    else:
        debuts = [ev.debut]

    return sorted(set(debuts))


# ----------------------------------------------------------------- selection

def occurrences(evenements: list[Evenement], maintenant: datetime) -> list[tuple[datetime, Evenement]]:
    """Rend les occurrences a venir, overrides et annulations appliquees."""
    horizon = maintenant + HORIZON
    # Un RECURRENCE-ID ne designe une exception que s'il existe un evenement
    # maitre du meme UID dans le flux. Google developpe les recurrences dans
    # le flux public : chaque instance arrive seule, avec un RECURRENCE-ID
    # mais sans maitre. Ces instances-la sont des evenements autonomes.
    maitres = {e.uid for e in evenements if e.recurrence_id is None}
    overrides = {
        (e.uid, e.recurrence_id): e
        for e in evenements
        if e.recurrence_id is not None and e.uid in maitres
    }
    resultats: list[tuple[datetime, Evenement]] = []
    for ev in evenements:
        if ev.annule:
            continue
        if ev.recurrence_id is not None and ev.uid in maitres:
            continue
        for debut in developper(ev, horizon):
            remplacant = overrides.get((ev.uid, debut))
            if remplacant is not None:
                if remplacant.annule:
                    continue
                resultats.append((remplacant.debut, remplacant))
            else:
                resultats.append((debut, ev))
    # une occurrence compte tant qu'elle n'est pas terminee
    return sorted(
        (d, e) for d, e in resultats if d + e.duree > maintenant and d <= horizon
    )


def choisir(evenements: list[Evenement], maintenant: datetime):
    """Rend (debut, evenement, avertissement)."""
    toutes = occurrences(evenements, maintenant)
    if not toutes:
        return None, None, "aucune occurrence a venir dans l'agenda"

    nommees = [(d, e) for d, e in toutes if FILTRE.search(e.titre)]
    if nommees:
        debut, ev = nommees[0]
        return debut, ev, ""

    longues = [(d, e) for d, e in toutes if e.duree >= DUREE_MIN]
    if longues:
        debut, ev = longues[0]
        return debut, ev, (
            "aucun titre ne correspond au filtre (agenda partage en mode "
            "libre/occupe ?) : repli sur le creneau le plus long"
        )
    debut, ev = toutes[0]
    return debut, ev, "ni titre ni duree exploitables : premiere occurrence retenue"


# ------------------------------------------------------------ ecriture HTML

def formater(debut: datetime, ev: Evenement) -> dict[str, str]:
    fin = debut + ev.duree

    def heure(moment: datetime) -> str:
        return f"{moment.hour}h{moment.minute:02d}" if moment.minute else f"{moment.hour}h"

    valeurs = {
        "jour": JOURS[debut.weekday()],
        "date": f"{debut.day} {MOIS[debut.month - 1]} {debut.year}",
        "debut": heure(debut),
        "fin": heure(fin),
    }
    if ev.lieu:
        nom, _, reste = ev.lieu.partition(",")
        valeurs["lieu"] = nom.strip()
        if reste.strip():
            valeurs["adresse"] = reste.strip()
    return valeurs


def remplir(page: str, valeurs: dict[str, str]) -> tuple[str, list[str]]:
    modifies = []
    for cle, valeur in valeurs.items():
        motif = re.compile(
            r'<span[^>]*\bdata-cal="' + re.escape(cle) + r'"[^>]*>.*?</span>',
            re.S,
        )
        trouves = motif.findall(page)
        if not trouves:
            continue
        if len(trouves) > 1:
            raise SystemExit(f"erreur : data-cal=\"{cle}\" apparait {len(trouves)} fois")
        page = motif.sub(
            f'<span data-cal="{cle}">{html.escape(valeur)}</span>', page, count=1
        )
        modifies.append(cle)
    return page, modifies


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--check", action="store_true", help="affiche sans ecrire")
    parseur.add_argument("--page", default="index.html")
    args = parseur.parse_args()

    requete = urllib.request.Request(ICS_URL, headers={"User-Agent": "repair-cafe-bourg/1.0"})
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        texte = reponse.read().decode("utf-8", errors="replace")

    evenements = parser(texte)
    if not evenements:
        print("erreur : aucun evenement dans le flux", file=sys.stderr)
        return 1

    maintenant = datetime.now(PARIS)
    debut, ev, avertissement = choisir(evenements, maintenant)
    if debut is None:
        print(f"erreur : {avertissement}", file=sys.stderr)
        return 1
    if avertissement:
        print(f"attention : {avertissement}", file=sys.stderr)

    valeurs = formater(debut, ev)
    print(f"{len(evenements)} evenements lus, prochaine seance retenue :")
    print(f"  {valeurs['jour']} {valeurs['date']}, {valeurs['debut']} - {valeurs['fin']}")
    print(f"  titre « {ev.titre or '(vide)'} », duree {ev.duree}")
    if ev.lieu:
        print(f"  lieu  « {ev.lieu} »")

    with open(args.page, encoding="utf-8") as fichier:
        page = fichier.read()
    nouvelle, modifies = remplir(page, valeurs)
    if not modifies:
        print("erreur : aucun element data-cal trouve dans la page", file=sys.stderr)
        return 1
    print(f"champs remplis : {', '.join(modifies)}")

    if args.check:
        print("--check : page non modifiee")
        return 0
    if nouvelle == page:
        print("page deja a jour")
        return 0
    with open(args.page, "w", encoding="utf-8") as fichier:
        fichier.write(nouvelle)
    print(f"{args.page} mis a jour")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
