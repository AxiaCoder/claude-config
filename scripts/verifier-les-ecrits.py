#!/usr/bin/env python3
"""Parcourt les fichiers `.md` des dossiers donnes et signale trois defauts d'ecriture.

  RENVOI MORT     un `/nom-de-commande` sans commande ni skill de ce nom
  FICHIER ABSENT  un `chemin/vers/fichier.md` qui n'existe pas
  NOTE EN DOUBLE  un titre de note — `📌 **...**` — ecrit deux fois dans le meme fichier

Les deux premiers sont ce qu'une suppression laisse derriere elle ; le troisieme, ce qu'un
remplacement mal borne produit.

    python3 scripts/verifier-les-ecrits.py <a-balayer>... [--aussi <a-resoudre>...]

Les dossiers `--aussi` ne sont pas balayes : ils servent seulement a resoudre un chemin
relatif a une racine ou le fichier qui le cite ne vit pas.

Une ligne par constat, `fichier:ligne` puis la cible. Sortie 1 s'il y en a, 0 sinon.

⛔ Il ne dit pas si une note est devenue fausse : ca se relit, ca ne se compte pas.
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys

# Un marqueur en debut de ligne, puis un titre en gras.
NOTE = re.compile(r"^[📌⚠️⛔✅🔑🔴] \*\*(.{12,60})", re.M)

# Les accents graves sont obligatoires : sans eux, toute barre oblique de prose compte.
RENVOI_COMMANDE = re.compile(r"`/([a-z][a-z0-9-]{2,30})`")

# Un separateur est obligatoire : un nom nu est un raccourci, un chemin est verifiable.
RENVOI_FICHIER = re.compile(r"`([a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)+\.(?:md|py|sh|ps1|json))`")

# Dossiers de matiere brute : ils portent des textes ecrits ailleurs, qui citent ailleurs.
IGNORES = {".git", "synced", "briefs", "corpus", "archive", "node_modules"}

# Chemins qui designent un fichier du projet ou la commande s'execute, jamais d'un depot balaye.
PROPRES_AU_PROJET = (".claude/surcharges/",)

# Ce qui ressemble a un renvoi de commande sans en etre un : des mots courants, et des
# commandes citees pour dire qu'on ne les emploie pas — celles du harnais ou d'un autre outil.
FAUX_AMIS = {
    "dev", "tester", "reviewer", "main", "master", "tmp", "usr", "etc", "var", "srv",
    "home", "bin", "opt", "dist", "build", "out", "clear", "usage", "login", "help",
    "compact", "resume", "config", "model", "agents", "skills", "commands", "hooks",
    "code-review", "skill-test",
}


def commandes_connues(racine: pathlib.Path) -> set[str]:
    """Rend le nom de chaque commande et de chaque skill trouves sous cette racine."""
    noms = {p.stem for p in racine.rglob("commands/*.md")}
    noms |= {p.parent.name for p in racine.rglob("skills/*/SKILL.md")}
    noms |= {p.stem for p in racine.rglob(".claude/commands/*.md")}
    return noms


def renvoi_verifiable(
    cible: str, depuis: pathlib.Path, racines: list[pathlib.Path], balayee: pathlib.Path
) -> bool:
    """Dit si ce chemin peut etre cherche, et n'est pas deja trouve.

    Un chemin absolu, une URL, un artefact d'execution, un renvoi vers un autre depot et un
    fichier propre au projet de l'utilisateur sont hors de portee : le premier segment d'un
    chemin verifiable est un dossier connu. Un fichier propre au projet redevient verifiable
    quand `balayee`, la racine du fichier qui le cite, versionne elle-meme ce dossier.
    """
    if cible.startswith(("http", "~", "/", "./")) or "*" in cible:
        return False
    if cible.startswith(PROPRES_AU_PROJET) and not any(
        (balayee / prefixe).is_dir() for prefixe in PROPRES_AU_PROJET
    ):
        return False
    if (depuis / cible).exists() or any((r / cible).exists() for r in racines):
        return False
    return any((r / cible.split("/")[0]).is_dir() for r in racines)


def verifier(racines: list[pathlib.Path], aussi: list[pathlib.Path]) -> list[str]:
    """Rend un constat par defaut trouve dans les `racines`, vide si tout va bien."""
    constats: list[str] = []
    connues: set[str] = set()
    for racine in racines + aussi:
        connues |= commandes_connues(racine)

    for racine in racines:
        for p in racine.rglob("*.md"):
            if any(part in IGNORES for part in p.parts):
                continue
            texte = p.read_text(encoding="utf-8", errors="ignore")
            rel = p.relative_to(racine)
            ligne_de = lambda i: texte[:i].count("\n") + 1

            for m in RENVOI_COMMANDE.finditer(texte):
                if m.group(1) not in FAUX_AMIS and m.group(1) not in connues:
                    constats.append(f"RENVOI MORT   {rel}:{ligne_de(m.start())}  /{m.group(1)}")

            for m in RENVOI_FICHIER.finditer(texte):
                if renvoi_verifiable(m.group(1), p.parent, racines + aussi, racine):
                    constats.append(f"FICHIER ABSENT {rel}:{ligne_de(m.start())}  {m.group(1)}")

            titres = collections.Counter(m.group(1).strip() for m in NOTE.finditer(texte))
            for titre, n in titres.items():
                if n > 1:
                    constats.append(f"NOTE EN DOUBLE {rel}  ×{n}  {titre[:52]}")

    return constats


def main() -> int:
    """Balaye les dossiers donnes en argument et rend 1 si un defaut est trouve."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if not args:
        print(
            f"usage: {pathlib.Path(sys.argv[0]).name} <a-balayer>... [--aussi <a-resoudre>...]",
            file=sys.stderr,
        )
        return 2

    aussi: list[pathlib.Path] = []
    if "--aussi" in args:
        coupe = args.index("--aussi")
        aussi = [pathlib.Path(a).resolve() for a in args[coupe + 1:]]
        args = args[:coupe]

    racines = [pathlib.Path(a).resolve() for a in args]
    for r in racines + aussi:
        if not r.is_dir():
            print(f"⛔ {r} n'est pas un dossier", file=sys.stderr)
            return 2

    constats = verifier(racines, aussi)
    for c in constats:
        print(c)
    print(f"\n{len(constats)} constat(s)" if constats else "\nrien a signaler")
    return 1 if constats else 0


if __name__ == "__main__":
    raise SystemExit(main())
