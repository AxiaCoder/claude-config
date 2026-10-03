#!/usr/bin/env python3
"""Cas de test de statusline.py. Sortie 0 si tous passent.

Se lance après toute modification du rendu : `python3 hooks/statusline.test.py`
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

_ICI = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("statusline", _ICI / "statusline.py")
_statusline = importlib.util.module_from_spec(_spec)
sys.modules["statusline"] = _statusline
_spec.loader.exec_module(_statusline)

COMPLET = {
    "model": {"display_name": "Opus"},
    "workspace": {"current_dir": str(_ICI)},
    "context_window": {"used_percentage": 23},
    "rate_limits": {
        "five_hour": {"used_percentage": 67},
        "seven_day": {"used_percentage": 91},
    },
    "pr": {"number": 95},
}


def lancer(entree: str) -> subprocess.CompletedProcess:
    """Lance statusline.py en sous-processus avec entree sur stdin, sortie en octets."""
    return subprocess.run(
        [sys.executable, str(_ICI / "statusline.py")],
        input=entree.encode("utf-8"), capture_output=True, timeout=30,
    )


def verifier_ordre() -> list[str]:
    """JSON complet : tous les segments présents, dans l'ordre, sans retour final."""
    defauts: list[str] = []
    ligne = _statusline.render(COMPLET)
    reperes = ["\U0001F916", "\U0001F4C1", "\U0001F9E0", "⏳ \033[2m5h", "⏳ \033[2m7d", "\U0001F500"]
    positions = [ligne.find(r) for r in reperes]
    if -1 in positions:
        defauts.append(f"segment manquant : {[r for r, p in zip(reperes, positions) if p == -1]}")
    elif positions != sorted(positions):
        defauts.append(f"ordre des segments {positions}")
    if "PR #95" not in ligne:
        defauts.append("référence de PR absente")
    sortie = lancer(json.dumps(COMPLET)).stdout
    if sortie.endswith(b"\n"):
        defauts.append("retour à la ligne final")
    if sortie.decode("utf-8") != ligne:
        defauts.append("sortie du processus différente du rendu")
    return defauts


def verifier_omission() -> list[str]:
    """Champ absent : son segment disparaît, les autres restent."""
    defauts: list[str] = []
    for cle, repere in (("model", "\U0001F916"), ("context_window", "\U0001F9E0"),
                        ("rate_limits", "⏳"), ("pr", "\U0001F500")):
        charge = {k: v for k, v in COMPLET.items() if k != cle}
        ligne = _statusline.render(charge)
        if repere in ligne:
            defauts.append(f"{cle} absent mais segment rendu")
        if "\U0001F4C1" not in ligne:
            defauts.append(f"{cle} absent a emporté le dossier")
    if _statusline.render({}) != "":
        defauts.append("charge vide : ligne non vide")
    return defauts


def verifier_couleurs() -> list[str]:
    """Seuils 50/80 : vert à 23, orange à 67, rouge à 91."""
    defauts: list[str] = []
    for pct, couleur, nom in ((23, _statusline.GREEN, "vert"),
                              (67, _statusline.YELLOW, "orange"),
                              (91, _statusline.RED, "rouge")):
        ligne = _statusline.render({"context_window": {"used_percentage": pct}})
        if f"{_statusline.BOLD}{couleur}{pct}%" not in ligne:
            defauts.append(f"{pct}% pas en {nom}")
    return defauts


def verifier_invalide() -> list[str]:
    """JSON invalide ou inattendu : sortie 0, rien sur stderr."""
    defauts: list[str] = []
    for entree in ("pas du json", "", "[1, 2]", '{"model": "plat"}'):
        resultat = lancer(entree)
        if resultat.returncode != 0 or resultat.stderr:
            defauts.append(f"{entree!r} : code {resultat.returncode}, stderr {resultat.stderr[:80]!r}")
    return defauts


def verifier_bornes() -> list[str]:
    """Bornes de la barre : 0 vide, 100 pleine, hors plage ramené dans 0-100."""
    defauts: list[str] = []
    s = _statusline
    for pct, pleins, affiche, couleur in ((0, 0, 0, s.GREEN), (100, 10, 100, s.RED),
                                          (150, 10, 100, s.RED), (-5, 0, 0, s.GREEN)):
        rendu = s.bar(pct)
        if rendu.count("█") != pleins or rendu.count("░") != 10 - pleins:
            defauts.append(f"{pct}% : {rendu.count('█')} pleins, {rendu.count('░')} vides")
        if f"{s.BOLD}{couleur}{affiche}%" not in rendu:
            defauts.append(f"{pct}% : valeur affichée ou couleur fausse, {rendu!r}")
    if s.bar(50, 6).count("█") != 3 or s.bar(50, 6).count("░") != 3:
        defauts.append("barre de 6 à 50 % : pas 3 pleins + 3 vides")
    return defauts


def verifier_seuils() -> list[str]:
    """Seuils exacts : 49 vert, 50 orange, 79 orange, 80 rouge."""
    defauts: list[str] = []
    s = _statusline
    for pct, couleur, nom in ((49, s.GREEN, "vert"), (50, s.YELLOW, "orange"),
                              (79, s.YELLOW, "orange"), (80, s.RED, "rouge")):
        if s.level_color(pct) != couleur:
            defauts.append(f"{pct}% pas en {nom}")
    return defauts


def verifier_decimal() -> list[str]:
    """Pourcentage décimal : affiché arrondi à l'entier, sans virgule, barre arrondie."""
    defauts: list[str] = []
    ligne = _statusline.render({"context_window": {"used_percentage": 67.4}})
    if "67%" not in ligne or "67.4" in ligne:
        defauts.append(f"67.4 mal affiché : {ligne!r}")
    if ligne.count("█") != 7:
        defauts.append(f"67.4 : {ligne.count('█')} pleins au lieu de 7")
    ligne = _statusline.render({"rate_limits": {"five_hour": {"used_percentage": 12.6}}})
    if "13%" not in ligne:
        defauts.append(f"12.6 pas arrondi à 13 : {ligne!r}")
    return defauts


def verifier_pr_mr() -> list[str]:
    """Référence : « MR ! » quand kind vaut mr, « PR # » sinon ; numéro 0 ou absent omis."""
    defauts: list[str] = []
    for pr, attendu in (({"number": 12, "kind": "mr"}, "MR !12"),
                        ({"number": 12, "kind": "pr"}, "PR #12"),
                        ({"number": 12}, "PR #12")):
        ligne = _statusline.render({"pr": pr})
        if attendu not in ligne:
            defauts.append(f"{pr} : {attendu} absent de {ligne!r}")
    for pr in ({"number": 0}, {"kind": "mr"}, {}):
        if "\U0001F500" in _statusline.render({"pr": pr}):
            defauts.append(f"{pr} : segment PR rendu sans numéro")
    return defauts


def verifier_dossier() -> list[str]:
    """Dossier : branche dans un dépôt git, pas de branche hors dépôt ou dossier absent."""
    import tempfile
    defauts: list[str] = []
    branche = subprocess.run(["git", "-C", str(_ICI), "branch", "--show-current"],
                             capture_output=True, text=True).stdout.strip()
    ligne = _statusline.render({"workspace": {"current_dir": str(_ICI)}})
    if "\U0001F4C1" not in ligne or "hooks" not in ligne:
        defauts.append(f"dossier du dépôt mal rendu : {ligne!r}")
    if branche and f"\U0001F33F {_statusline.CYAN}{branche}" not in ligne:
        defauts.append(f"branche {branche} absente dans le dépôt")
    with tempfile.TemporaryDirectory() as hors_depot:
        nom = pathlib.Path(hors_depot).name
        ligne = _statusline.render({"workspace": {"current_dir": hors_depot + "/"}})
        if "\U0001F33F" in ligne:
            defauts.append(f"branche rendue hors dépôt : {ligne!r}")
        if f"{_statusline.BLUE}{nom}{_statusline.RESET}" not in ligne:
            defauts.append(f"nom du dossier avec séparateur final mal rendu : {ligne!r}")
    ligne = _statusline.render({"cwd": str(_ICI / "inexistant")})
    if "inexistant" not in ligne or "\U0001F33F" in ligne:
        defauts.append(f"repli sur cwd ou dossier absent mal rendu : {ligne!r}")
    return defauts


def main() -> int:
    """Joue toutes les vérifications et rend 1 si l'une d'elles relève un défaut."""
    echec = False
    for nom, verif in (("ordre des segments", verifier_ordre),
                       ("champ absent omis", verifier_omission),
                       ("couleurs 23/67/91", verifier_couleurs),
                       ("JSON invalide -> exit 0", verifier_invalide),
                       ("bornes 0/100/hors plage", verifier_bornes),
                       ("seuils exacts 49/50/79/80", verifier_seuils),
                       ("pourcentage décimal arrondi", verifier_decimal),
                       ("PR # vs MR !", verifier_pr_mr),
                       ("dossier dans / hors dépôt git", verifier_dossier)):
        defauts = verif()
        echec = echec or bool(defauts)
        print(f"{'  ok ' if not defauts else 'ECHEC'} {nom}")
        for defaut in defauts:
            print(f"  {defaut}")
    return 1 if echec else 0


if __name__ == "__main__":
    raise SystemExit(main())
