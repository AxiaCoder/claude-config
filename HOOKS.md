# Les hooks — déclarer, vérifier

> **Comment déclarer un hook dans ce dépôt, et comment vérifier qu'il tourne sur un poste.**
> Ce que fait chaque hook → [README](./README.md#les-hooks).

---

## La procédure, dans cet ordre

1. **Ce qu'appelle un hook d'abord.** Un hook déclaré dont le script ou l'interpréteur manque
   **échoue à chaque appel d'outil**.
2. **Déclarer les hooks** dans l'overlay de l'OS — `settings.macos.json` ou
   `settings.windows.json`. ⛔ Avec `{{CLAUDE_HOME}}` pour le chemin, **jamais un chemin absolu**,
   et l'interpréteur de la plateforme : `python3` sur macOS, `{{PYTHON}}` sous Windows.
3. **Rendre la configuration** : `./install.sh` ou `.\install.ps1`.
4. **Vérifier** — la section suivante, qui n'est pas optionnelle.

⚠️ **Les enveloppes `.sh` ne s'exécutent pas sous Windows.** Là-bas, la déclaration appelle le `.py`
directement.

---

## ⛔ La vérification, qui n'est pas optionnelle

**Un hook déclaré dont le script ou le binaire manque échoue à chaque appel d'outil**, et rien ne
le signale : la réponse aboutit, le hook coûte un démarrage d'interpréteur pour rien.

🔴 **Elle se lance après chaque fusion qui touche aux hooks, pas seulement à l'installation.** La
configuration rendue retarde sur le dépôt jusqu'au prochain `install.sh` : un fichier renommé côté
dépôt laisse une déclaration morte côté poste, et le dépôt a l'air propre.

**Sur Unix** — le script ci-dessous, écrit dans un fichier avec Write, puis `python3 <fichier>` :

```python
import json, os, pathlib, shutil

def cibles_de(commande):
    """Rend les mots d'une commande de hook qui désignent un fichier à trouver.

    Tout mot portant un séparateur de chemin ou une extension de script compte ; à
    défaut le premier mot, qui est alors un binaire cherché dans le PATH.
    """
    mots = [m.strip('"\'') for m in commande.split()]
    chemins = [m for m in mots if "/" in m or "\\" in m or m.endswith((".py", ".sh", ".ps1"))]
    return chemins or mots[:1]

for source in ("settings.json", "settings.local.json"):
    chemin = pathlib.Path.home() / ".claude" / source
    if not chemin.exists():
        continue
    for evenement, blocs in json.loads(chemin.read_text()).get("hooks", {}).items():
        for bloc in blocs:
            for hook in bloc.get("hooks", []):
                for cible in cibles_de(hook.get("command", "")):
                    if not (os.path.exists(cible) or shutil.which(cible)):
                        print(f"MANQUANT  {source:22} {evenement:15} {cible}")
print("verification terminee")
```

**Sur Windows** — le script ci-dessous, écrit dans un fichier `.ps1` avec Write, puis
`pwsh -File <fichier>` (`powershell -File` en 5.1) :

```powershell
foreach ($source in @("settings.json", "settings.local.json")) {
  $f = Join-Path $HOME ".claude\$source"
  if (-not (Test-Path $f)) { continue }
  $reglages = Get-Content $f -Raw | ConvertFrom-Json
  if (-not $reglages.hooks) { continue }
  $reglages.hooks.PSObject.Properties | ForEach-Object {
    $evenement = $_.Name
    $_.Value | ForEach-Object { $_.hooks } | Where-Object { $_.command } | ForEach-Object {
      $mots = @(($_.command -split '\s+') | ForEach-Object { $_.Trim('"') })
      $cibles = @($mots | Where-Object { $_ -match '[\\/]' -or $_ -match '\.(py|sh|ps1)$' })
      if (-not $cibles) { $cibles = @($mots[0]) }
      foreach ($c in $cibles) {
        if (-not (Test-Path $c) -and -not (Get-Command $c -ErrorAction SilentlyContinue)) {
          "MANQUANT  $source  $evenement  $c"
        }
      }
    }
  }
}
```

⚠️ **Le contrôle regarde chaque mot qui désigne un fichier, pas seulement le premier.** Une commande
de la forme `python3 /chemin/hook.py` — sans guillemets, la forme que l'étape 2 préconise — ne
ferait sinon vérifier que `python3`, qui existe toujours. Et il lit `settings.local.json` en plus de
`settings.json`, les deux pouvant déclarer.

✅ **Aucune ligne `MANQUANT` = les hooks sont installés.**

⚠️ **Installé ne veut pas dire qu'il fait ce qu'il doit.** Ça se vérifie en lançant le hook **tel
que l'hôte le lance** : la commande exacte de sa déclaration dans `settings.json` — `guardrail.py`
appelé directement sur macOS, précédé de `{{PYTHON}}` sous Windows —, avec sur stdin la charge
JSON réelle de l'événement, chemins réels compris (`agent_transcript_path` pour
`collecteur-agents.py`). Ce qui tranche dépend du hook :

- **un hook de garde** (`guardrail.py`, `garde-push.py`) : son **code de sortie** — `2` refuse,
  `0` laisse passer — et le motif qu'il donne (JSON `decision`/`reason` sur stdout pour
  `guardrail.py`, message sur stderr pour `garde-push.py`) ;
- **un hook collecteur** (`collecteur-agents.py`) : il sort toujours `0`, son code ne dit rien. Ce
  qui tranche est ce qu'il a produit — sa ligne `… — envoye` ou `… — en attente`, et
  `~/.claude/telemetrie-agents/en-attente.jsonl` quand l'envoi a échoué.

⚠️ **`guardrail.py` garde un état** (`~/.claude/hook-state/`) et refuse au 4ᵉ appel identique. Le
tester avec `HOME` sur un dossier jetable (`USERPROFILE` sous Windows) et la charge lue depuis un
fichier : sinon les essais donnent un faux refus, s'écrivent dans l'état de la session en cours, et
une charge de refus passée en ligne est bloquée par le `guardrail.py` installé avant d'atteindre
celui qu'on teste.

---

## Ce dont chaque brique a besoin

| Brique | Ce qu'elle demande |
|---|---|
| `guardrail.py` | rien — bibliothèque standard. **Commandes destructrices : outil `Bash` seulement, pas l'outil PowerShell** |
| `collecteur-agents.py` | une adresse de collecte dans `env` (dossier perso), et une instance VictoriaMetrics derrière — celle de [home-server-telemetry](https://github.com/AxiaCoder/home-server-telemetry), par exemple |
| `session-git-context`, `post-write-lint` | `sh` sur macOS ; `pwsh` (PowerShell 7) sous Windows. `post-write-lint` demande aussi `pnpm` dans un projet AdonisJS |
| `statusline.py` | rien — bibliothèque standard |
| `garde-push.py` | python — bibliothèque standard. Refuse une commande de l'agent qui désarmerait `git-hooks/pre-push` |
| `git-hooks/` (`pre-push` et le relais `_relais`) | git et `sh` (celui de Git for Windows sous Windows). Hooks git, pas hooks Claude ; chacun relaie au hook du même nom dans `.git/hooks/` du dépôt — détail au README, § Hooks git globaux. Ils sont activés par `install` via `core.hooksPath` global, **sauf si un autre dossier y est déjà déclaré** — l'installation avertit et n'écrase pas. Contrôle : `git config --global --get core.hooksPath` |

⚠️ **`OTEL_LOG_TOOL_DETAILS=1` (`settings.base.json`) ne met aujourd'hui que des noms d'agents et de
skills sur les métriques.** Il déverrouille aussi, sur les *événements* et les *traces*, la commande
Bash complète, les chemins de fichiers et les diffs. Les deux sont coupés (`OTEL_LOGS_EXPORTER=none`,
pas d'exporteur de traces) : **qui les active envoie ces contenus aux points de collecte** — le
décider en connaissance de cause, ou retirer ce réglage d'abord.

---

## ⚠️ Un piège qui coûte un essai

**`"hooks": {}` dans un fichier passé à `--settings` ne désactive rien** — les hooks
s'additionnent entre niveaux de réglages. La clé qui coupe est **`disableAllHooks: true`**. Sans
elle, un essai « avec » contre « sans » compare deux fois « avec ».
