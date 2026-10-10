# Dépendances externes

Tout ce que claude-config installe ou suppose présent hors du dépôt. ⛔ **Rien n'est installé
qui ne figure ici** : un outil ajouté à `install.sh` / `install.ps1` ou à un hook entre dans ce
fichier dans le même commit.

## Installé par claude-config

### betterleaks

| | |
|---|---|
| Ce que c'est | Détecteur de secrets (jetons, clés privées…), successeur de gitleaks |
| Version | **1.9.0**, épinglée dans [`git-hooks/betterleaks.version`](./git-hooks/betterleaks.version) |
| Source | `https://github.com/betterleaks/betterleaks/releases/download/v1.9.0/betterleaks_1.9.0_<plateforme>.tar.gz` (`.zip` sous Windows) |
| Empreinte | sha256 par plateforme dans `git-hooks/betterleaks.version`, recopié du `checksums.txt` de la release. L'installation refuse un asset dont le sha256 diffère |
| Où | `~/.claude/bin/betterleaks` (Windows : `betterleaks.exe`) |
| À quoi il sert | Le garde secrets du `pre-commit` et du `pre-push` globaux (`git-hooks/_garde-secrets`), lancé avec `--validation=false` : aucun appel réseau |
| Le refuser | `bash install.sh --sans-externes` / `.\install.ps1 -SansExternes` : rien n'est téléchargé, le garde secrets est désactivé. Choix mémorisé dans `~/.claude/claude-config.sans-externes` ; `--avec-externes` / `-AvecExternes` le défait |
| Le retirer | supprimer `~/.claude/bin/betterleaks` (ou `.exe`), puis relancer l'installation avec `--sans-externes` — sans quoi la passe suivante le repose et, d'ici là, le `pre-commit` refuse les commits et le `pre-push` les pushes |

**Monter de version.** Lire les assets et le `checksums.txt` de la nouvelle release, reporter
version et sha256 dans `git-hooks/betterleaks.version`, vérifier les options du garde sur le
binaire (`betterleaks git --help`), relancer `sh git-hooks/garde-secrets.test.sh` après
l'installation : son essai réel tourne avec le binaire de `~/.claude/bin`.

## Supposé présent — installé par l'utilisateur

| Outil | Qui s'en sert | Sans lui |
|---|---|---|
| Claude Code | tout | l'installation s'arrête (`~/.claude` absent) |
| `git` | installation, hooks git, `statusline.py` | rien ne marche |
| Python 3, bibliothèque standard (`python3` ; `py -3` ou `python` sous Windows) | installation (rendu des fichiers), hooks Claude `*.py` | l'installation s'arrête |
| PowerShell 7 (`pwsh`), Windows | `install.ps1`, hooks `session-git-context.ps1`, `post-write-lint.ps1` | l'installation ne se lance pas |
| Git for Windows (`sh`), Windows | les hooks git, écrits en `sh` | les hooks git ne tournent pas |
| `curl` | `install.sh` (téléchargement de betterleaks), `_garde-public` (visibilité d'un dépôt) | betterleaks non installé ; `_garde-public` se replie sur `gh` |
| `tar`, `shasum` ou `sha256sum` | `install.sh` (extraction, empreinte de betterleaks) | betterleaks non installé |
| `gh`, connecté | `_garde-public` (repli pour la visibilité d'un dépôt) | push bloqué si l'API GitHub ne répond pas non plus |
| `ssh` | `_garde-public` (résolution d'un alias SSH) | un alias vers GitHub n'est pas reconnu |
| `pnpm` | `post-write-lint`, dans un projet AdonisJS | le lint après écriture ne tourne pas |
| `openssl` | `git-hooks/garde-secrets.test.sh`, essai réel seulement | le cas « clé privée PEM » est sauté |
| une instance VictoriaMetrics et son adresse dans `env` | `collecteur-agents.py` | rien n'est envoyé |
