#!/usr/bin/env python3
# Adapted from glebis/claude-skills (the-goal), commit 3b88261, MIT License,
# Copyright (c) 2025-2026 Gleb Kalinin.
"""Pick the cheapest automation form that relieves the constraint, from closed facts.

Claude gathers the facts; this script decides, so the choice is repeatable. The
forms run from cheapest (0) to most expensive (7); the decision tree checks the
most demanding facts first, so the first form it returns is the cheapest one
that still meets every fact.

Facts (booleans; omitted = false), plus one three-valued fact:
  exploitation_suffit                 exploiting the constraint as it is is enough
  jugement                            "aucun" | "une_etape" | "chaque_etape" — where judgment is needed
  evenement_declencheur               a fact (file, message, state change) triggers a fixed action
  colle_entre_services                glue between services, no judgment
  logique_a_tester                    fixed steps whose logic must be tested and versioned
  lance_par_l_utilisateur             the user starts it by hand
  sans_surveillance                   runs with no one watching
  en_continu                          must run continuously
Modifier:
  ne_doit_jamais_echouer_en_silence   a failure must always surface

Decision order:
  1. exploitation_suffit                          -> 0 Ne rien construire
  2. en_continu                                   -> 7 Service permanent
  3. jugement chaque_etape, sans_surveillance
     and not lance_par_l_utilisateur              -> 6 Agent autonome
  4. jugement chaque_etape                        -> 5 Commande lancée à la main
  5. jugement une_etape, lance_par_l_utilisateur  -> 5 Commande lancée à la main
  6. jugement une_etape                           -> 4 Script avec une étape d'IA
  7. logique_a_tester or lance_par_l_utilisateur
     or sans_surveillance                         -> 3 Script déterministe planifié
  8. colle_entre_services                         -> 2 Relier des services
  9. evenement_declencheur                        -> 1 Réagir à un événement
  10. nothing else                                -> no form (facts missing)

--json keys may use hyphens or underscores; facts must be exactly true/false.
An unknown key or flag, a non-boolean fact, an empty --json or a bad jugement
(case-sensitive) prints {"error": ...} instead of a decision.

Usage:
  choisir_la_forme.py --jugement une-etape --sans-surveillance
  choisir_la_forme.py --json '{"jugement": "aucun", "colle_entre_services": true}'

Outputs JSON: {forme, nom, raison, modificateurs, remarques, faits}. Exit 0 always.
"""
import argparse
import json

FORMES = {
    0: "Ne rien construire",
    1: "Réagir à un événement",
    2: "Relier des services",
    3: "Script déterministe planifié",
    4: "Script avec une étape d'IA",
    5: "Commande lancée à la main",
    6: "Agent autonome",
    7: "Service permanent",
}

BOOLEENS = [
    "exploitation_suffit",
    "evenement_declencheur",
    "colle_entre_services",
    "logique_a_tester",
    "lance_par_l_utilisateur",
    "sans_surveillance",
    "en_continu",
    "ne_doit_jamais_echouer_en_silence",
]

JUGEMENTS = ("aucun", "une_etape", "chaque_etape")


def forme_de_base(f):
    """Return (form number or None, reason) for the facts dict f, per the decision order."""
    jugement = f["jugement"]
    if f["exploitation_suffit"]:
        return 0, "L'exploitation du goulot suffit : rien à construire."
    if f["en_continu"]:
        return 7, "Doit tourner en continu : un service permanent."
    if jugement == "chaque_etape":
        if f["sans_surveillance"] and not f["lance_par_l_utilisateur"]:
            return 6, "Jugement à chaque étape, sans personne pour le lancer ni le suivre."
        return 5, "Jugement à chaque étape, avec l'utilisateur présent : une commande qu'il lance."
    if jugement == "une_etape":
        if f["lance_par_l_utilisateur"]:
            return 5, "Une étape de jugement, lancée par l'utilisateur : une commande à la main."
        return 4, "Tout est fixe sauf un jugement : un script avec une seule étape d'IA."
    if f["logique_a_tester"] or f["lance_par_l_utilisateur"] or f["sans_surveillance"]:
        return 3, "Étapes fixes, sans jugement : un script déterministe, testé et versionné."
    if f["colle_entre_services"]:
        return 2, "Colle entre services, sans jugement : relier les services."
    if f["evenement_declencheur"]:
        return 1, "Un fait déclenche une action fixe : réagir à l'événement."
    return None, "Aucun fait ne désigne une forme : préciser les faits."


def remarques(forme, f):
    """Return the advisory notes that apply to the chosen form and facts."""
    notes = []
    if forme == 3 and f["lance_par_l_utilisateur"]:
        notes.append("Lancé à la main : le script n'a pas besoin d'être planifié.")
    if forme == 3 and f["evenement_declencheur"]:
        notes.append("Déclenché par l'événement plutôt que par une horloge.")
    if forme == 4:
        notes.append("Découper : seule l'étape de jugement appelle l'IA, le reste reste déterministe.")
    if forme in (6, 7) and f["jugement"] == "chaque_etape":
        notes.append("IA à chaque étape sans humain : vérifier qu'une forme plus basse ne suffit pas.")
    if f["lance_par_l_utilisateur"] and f["sans_surveillance"]:
        notes.append("Faits contradictoires : lancé par l'utilisateur et sans surveillance.")
    return notes


def choisir(f):
    """Return the full decision for the normalized facts dict f."""
    forme, raison = forme_de_base(f)
    modificateurs = []
    notes = remarques(forme, f)
    if f["ne_doit_jamais_echouer_en_silence"]:
        if forme in (None, 0):
            notes.append("Rien ne tourne : le modificateur « ne doit jamais échouer en silence » ne s'applique pas.")
        else:
            modificateurs.append("échec signalé à chaque fois (alerte), reprise sur erreur, journal consultable")
    return {
        "forme": forme,
        "nom": FORMES.get(forme),
        "raison": raison,
        "modificateurs": modificateurs,
        "remarques": notes,
        "faits": f,
    }


def normaliser(data):
    """Turn a raw facts mapping into the normalized facts dict.

    Keys may use hyphens or underscores. Raises ValueError, naming the key, on an
    unknown key, a fact that is not exactly true/false, or a bad jugement (case-sensitive).
    """
    brut = {}
    for cle, valeur in data.items():
        nom = str(cle).replace("-", "_")
        if nom != "jugement" and nom not in BOOLEENS:
            raise ValueError(f"unknown fact: {cle}")
        brut[nom] = valeur
    jugement = str(brut.get("jugement", "aucun")).replace("-", "_")
    if jugement not in JUGEMENTS:
        raise ValueError(f"jugement must be one of {', '.join(JUGEMENTS)}")
    f = {}
    for fait in BOOLEENS:
        valeur = brut.get(fait, False)
        if not isinstance(valeur, bool):
            raise ValueError(f"{fait} must be true or false, got {json.dumps(valeur)}")
        f[fait] = valeur
    f["jugement"] = jugement
    return f


class ParseurSansSortie(argparse.ArgumentParser):
    """ArgumentParser that raises ValueError instead of printing usage and exiting 2."""

    def error(self, message):
        """Raise ValueError carrying argparse's message."""
        raise ValueError(message)


def main():
    """Parse flags or --json, print the decision as JSON; any bad input prints {"error": ...}."""
    ap = ParseurSansSortie(description="Pick the cheapest automation form from closed facts.")
    for fait in BOOLEENS:
        ap.add_argument("--" + fait.replace("_", "-"), action="store_true")
    ap.add_argument("--jugement", default="aucun",
                    help="aucun | une-etape | chaque-etape (default: aucun)")
    ap.add_argument("--json", help="JSON object of facts (overrides flags)")
    try:
        args = ap.parse_args()
        if args.json is not None:
            data = json.loads(args.json)
            if not isinstance(data, dict):
                raise ValueError("--json must be a JSON object of facts")
        else:
            data = {k: getattr(args, k) for k in BOOLEENS}
            data["jugement"] = args.jugement
        f = normaliser(data)
    except Exception as e:
        print(json.dumps({"error": f"bad input: {e}"}, ensure_ascii=False))
        return
    print(json.dumps(choisir(f), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
