#!/usr/bin/env python3
"""Tests du parseur d'agenda. Aucune dependance, aucun acces reseau.

    python3 scripts/test_prochaine_seance.py
"""

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import prochaine_seance as ps  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
ECHECS = []


def verifier(intitule, obtenu, attendu):
    if obtenu != attendu:
        ECHECS.append(f"{intitule}\n    attendu : {attendu}\n    obtenu  : {obtenu}")
        print(f"  ECHEC  {intitule}")
    else:
        print(f"  ok     {intitule}")


def flux(*evenements):
    corps = "".join(evenements)
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\n{corps}END:VCALENDAR\r\n"


def prochaine(texte, maintenant):
    debut, ev, avertissement = ps.choisir(ps.parser(texte), maintenant)
    if debut is None:
        return None
    return debut.strftime("%Y-%m-%d %H:%M")


MAINTENANT = datetime(2026, 8, 30, 12, 0, tzinfo=PARIS)

print("\n-- lecture de base --")

verifier(
    "depliage des lignes RFC 5545",
    ps.deplier("SUMMARY:Permanence du Repair\r\n  Cafe\r\nEND:VEVENT"),
    ["SUMMARY:Permanence du Repair Cafe", "END:VEVENT"],
)

verifier(
    "DTSTART en UTC converti vers Paris (heure d'ete)",
    ps.lire_date("20260905T153000Z", {}).strftime("%H:%M"),
    "17:30",
)
verifier(
    "DTSTART en UTC converti vers Paris (heure d'hiver)",
    ps.lire_date("20261114T153000Z", {}).strftime("%H:%M"),
    "16:30",
)
verifier(
    "DTSTART avec TZID",
    ps.lire_date("20260905T140000", {"TZID": "Europe/Paris"}).strftime("%H:%M"),
    "14:00",
)
verifier("desechappement", ps.echapper(r"Salle A\, rue B\; ici"), "Salle A, rue B; ici")

print("\n-- recurrences --")

verifier(
    "mensuel, 2e samedi du mois",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:a\r\n"
            "DTSTART;TZID=Europe/Paris:20260110T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260110T173000\r\n"
            "RRULE:FREQ=MONTHLY;BYDAY=2SA\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n"
        ),
        MAINTENANT,
    ),
    "2026-09-12 14:00",
)

verifier(
    "hebdomadaire un samedi sur deux",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:b\r\n"
            "DTSTART;TZID=Europe/Paris:20260905T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260905T173000\r\n"
            "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=SA\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n"
        ),
        MAINTENANT,
    ),
    "2026-09-05 14:00",
)

verifier(
    "dernier samedi du mois",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:c\r\n"
            "DTSTART;TZID=Europe/Paris:20260131T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260131T173000\r\n"
            "RRULE:FREQ=MONTHLY;BYDAY=-1SA\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n"
        ),
        MAINTENANT,
    ),
    "2026-09-26 14:00",
)

verifier(
    "EXDATE : la prochaine occurrence est sautee",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:d\r\n"
            "DTSTART;TZID=Europe/Paris:20260110T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260110T173000\r\n"
            "RRULE:FREQ=MONTHLY;BYDAY=2SA\r\n"
            "EXDATE;TZID=Europe/Paris:20260912T140000\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n"
        ),
        MAINTENANT,
    ),
    "2026-10-10 14:00",
)

verifier(
    "UNTIL : plus rien apres la borne",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:e\r\n"
            "DTSTART;TZID=Europe/Paris:20260110T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260110T173000\r\n"
            "RRULE:FREQ=MONTHLY;BYDAY=2SA;UNTIL=20260701T000000Z\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n"
        ),
        MAINTENANT,
    ),
    None,
)

print("\n-- exceptions et annulations --")

verifier(
    "RECURRENCE-ID : instance deplacee",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:f\r\n"
            "DTSTART;TZID=Europe/Paris:20260110T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260110T173000\r\n"
            "RRULE:FREQ=MONTHLY;BYDAY=2SA\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n",
            "BEGIN:VEVENT\r\nUID:f\r\n"
            "RECURRENCE-ID;TZID=Europe/Paris:20260912T140000\r\n"
            "DTSTART;TZID=Europe/Paris:20260913T100000\r\n"
            "DTEND;TZID=Europe/Paris:20260913T133000\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n",
        ),
        MAINTENANT,
    ),
    "2026-09-13 10:00",
)

verifier(
    "STATUS:CANCELLED : instance supprimee",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:g\r\n"
            "DTSTART;TZID=Europe/Paris:20260110T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260110T173000\r\n"
            "RRULE:FREQ=MONTHLY;BYDAY=2SA\r\n"
            "SUMMARY:Permanence\r\nEND:VEVENT\r\n",
            "BEGIN:VEVENT\r\nUID:g\r\n"
            "RECURRENCE-ID;TZID=Europe/Paris:20260912T140000\r\n"
            "DTSTART;TZID=Europe/Paris:20260912T140000\r\n"
            "DTEND;TZID=Europe/Paris:20260912T173000\r\n"
            "STATUS:CANCELLED\r\nSUMMARY:Permanence\r\nEND:VEVENT\r\n",
        ),
        MAINTENANT,
    ),
    "2026-10-10 14:00",
)

verifier(
    "instance orpheline (RECURRENCE-ID sans maitre) traitee comme autonome",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:h\r\nDTSTART:20260905T153000Z\r\n"
            "DTEND:20260905T210000Z\r\nRECURRENCE-ID:20260905T153000Z\r\n"
            "SUMMARY:Busy\r\nEND:VEVENT\r\n"
        ),
        MAINTENANT,
    ),
    "2026-09-05 17:30",
)

print("\n-- selection --")

DEUX = flux(
    "BEGIN:VEVENT\r\nUID:i\r\nDTSTART;TZID=Europe/Paris:20260905T200000\r\n"
    "DTEND;TZID=Europe/Paris:20260905T213000\r\nSUMMARY:Busy\r\nEND:VEVENT\r\n",
    "BEGIN:VEVENT\r\nUID:j\r\nDTSTART;TZID=Europe/Paris:20260912T140000\r\n"
    "DTEND;TZID=Europe/Paris:20260912T193000\r\nSUMMARY:Busy\r\nEND:VEVENT\r\n",
)
verifier(
    "sans titre exploitable, le creneau court est ecarte",
    prochaine(DEUX, MAINTENANT),
    "2026-09-12 14:00",
)

TITRES = flux(
    "BEGIN:VEVENT\r\nUID:k\r\nDTSTART;TZID=Europe/Paris:20260905T190000\r\n"
    "DTEND;TZID=Europe/Paris:20260905T230000\r\nSUMMARY:Reunion du bureau\r\nEND:VEVENT\r\n",
    "BEGIN:VEVENT\r\nUID:l\r\nDTSTART;TZID=Europe/Paris:20260912T140000\r\n"
    "DTEND;TZID=Europe/Paris:20260912T173000\r\nSUMMARY:Permanence mensuelle\r\nEND:VEVENT\r\n",
)
verifier(
    "avec des titres, le filtre prime sur la duree",
    prochaine(TITRES, MAINTENANT),
    "2026-09-12 14:00",
)

verifier(
    "une seance en cours reste affichee",
    prochaine(
        flux(
            "BEGIN:VEVENT\r\nUID:m\r\nDTSTART;TZID=Europe/Paris:20260830T100000\r\n"
            "DTEND;TZID=Europe/Paris:20260830T160000\r\nSUMMARY:Permanence\r\nEND:VEVENT\r\n"
        ),
        MAINTENANT,
    ),
    "2026-08-30 10:00",
)

print("\n-- ecriture HTML --")

PAGE = (
    '<p><span data-cal="jour" class="tbd">[JOUR]</span> '
    '<span data-cal="date" class="tbd">[DATE]</span></p>'
)
rendu, modifies = ps.remplir(PAGE, {"jour": "samedi", "date": "5 septembre 2026"})
verifier(
    "remplissage et retrait du surlignage tbd",
    rendu,
    '<p><span data-cal="jour">samedi</span> <span data-cal="date">5 septembre 2026</span></p>',
)
verifier("champs signales", sorted(modifies), ["date", "jour"])
verifier(
    "echappement HTML",
    ps.remplir('<span data-cal="lieu">x</span>', {"lieu": 'A & <b>B</b>'})[0],
    '<span data-cal="lieu">A &amp; &lt;b&gt;B&lt;/b&gt;</span>',
)

print()
if ECHECS:
    print(f"{len(ECHECS)} echec(s) :\n")
    for e in ECHECS:
        print(f"  {e}\n")
    sys.exit(1)
print("tous les tests passent")
