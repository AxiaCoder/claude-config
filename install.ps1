<#
.SYNOPSIS
  Monte claude-config dans ~/.claude sur cette machine.

.DESCRIPTION
  Les cinq dossiers de configuration deviennent des jonctions vers ce repo, et
  git-hooks devient le dossier de hooks git global (core.hooksPath), sauf si
  un autre dossier y est deja declare.
  CLAUDE.md, CAVEMAN.md et settings.json sont rendus : ils portent des chemins
  propres a la machine et ne peuvent pas etre lies. Le script est idempotent.

.PARAMETER Perso
  Dossier perso, optionnel : ses settings.json et settings.windows.json
  s'ajoutent par-dessus ceux du depot, et son CLAUDE.md prend la place de
  {{PERSO_CLAUDE_MD}}, avec {{PERSO}} remplace par le chemin du dossier. Son
  CLAUDE.complet.md, s'il en a un, remplace tout le CLAUDE.md du depot et fait
  ignorer son CLAUDE.md. Memorise dans
  ~/.claude/claude-config.perso, repris sans -Perso aux passes suivantes.

.PARAMETER WhatIfOnly
  Affiche les actions sans rien modifier.
#>
[CmdletBinding()]
param(
  [string] $Perso = '',
  [switch] $WhatIfOnly
)

$ErrorActionPreference = 'Stop'
$Repo        = $PSScriptRoot
$ClaudeHome  = Join-Path $HOME '.claude'
$LinkedDirs  = 'agents', 'commands', 'skills', 'hooks', 'git-hooks'
$Stamp       = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupDir   = Join-Path $ClaudeHome "config-backup-$Stamp"

function Step([string]$text) { Write-Host "  $text" }

if (-not (Test-Path $ClaudeHome)) { throw "'$ClaudeHome' n'existe pas." }
# Le lanceur py d'abord : le python.exe de WindowsApps n'est qu'un raccourci vers le Store.
$Python = $null
foreach ($candidat in @(@('py', '-3'), @('python'))) {
  if (-not (Get-Command $candidat[0] -ErrorAction SilentlyContinue)) { continue }
  $arguments = @($candidat | Select-Object -Skip 1) +
    @('-c', 'import sys; assert sys.version_info[0] == 3; print(sys.executable)')
  try {
    $sortie = & $candidat[0] @arguments 2>$null
    $code = $LASTEXITCODE
  } catch { continue }
  $exe = "$(@($sortie)[0])".Trim()
  if ($code -eq 0 -and $exe -and (Test-Path $exe)) { $Python = $exe; break }
}
if (-not $Python) { throw "Python 3 introuvable (ni py -3 ni python). Installe-le, puis relance." }
$PersoMemo = Join-Path $ClaudeHome 'claude-config.perso'
$PersoSource = '-Perso'
if (-not $Perso -and (Test-Path $PersoMemo)) {
  $Perso = "$(Get-Content $PersoMemo -Raw)".Trim()
  $PersoSource = "le memo $PersoMemo -- le supprimer pour s'en passer"
}
if ($Perso) {
  if (-not (Test-Path $Perso -PathType Container)) {
    throw "Le dossier perso est introuvable a '$Perso' (lu dans $PersoSource). Relance avec -Perso <dossier>."
  }
  $Perso = (Resolve-Path $Perso).Path
}

Write-Host "claude-config -> $ClaudeHome"
if ($WhatIfOnly) { Write-Host "(simulation, rien ne sera ecrit)" }

# --- Dossiers : sauvegarde puis jonction ---------------------------------
$agents = Get-Item (Join-Path $ClaudeHome 'agents') -Force -ErrorAction SilentlyContinue
$Premiere = -not ($agents -and $agents.LinkType -eq 'Junction' -and ($agents.Target -contains (Join-Path $Repo 'agents')))
# A la premiere passe, les fichiers que l'installation va reecrire sont ceux de
# l'utilisateur : ils partent dans la sauvegarde avant d'etre remplaces.
if ($Premiere) {
  foreach ($fichier in 'CLAUDE.md', 'CAVEMAN.md', 'settings.json') {
    $existant = Join-Path $ClaudeHome $fichier
    if (Test-Path $existant) {
      Step "$fichier : existant, sauvegarde dans $(Split-Path $BackupDir -Leaf)"
      if (-not $WhatIfOnly) {
        New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
        Copy-Item $existant (Join-Path $BackupDir $fichier)
      }
    }
  }
}
foreach ($dir in $LinkedDirs) {
  $target = Join-Path $ClaudeHome $dir
  $source = Join-Path $Repo $dir
  $item   = Get-Item $target -Force -ErrorAction SilentlyContinue

  if ($item -and $item.LinkType -eq 'Junction') {
    if ($item.Target -contains $source) { Step "$dir : jonction deja en place"; continue }
    Step "$dir : jonction vers une autre cible, remplacement"
    # Suppression du seul point de reparse : un Remove-Item recursif risquerait
    # de descendre dans la cible.
    if (-not $WhatIfOnly) { [System.IO.Directory]::Delete($target) }
  }
  elseif ($item) {
    Step "$dir : vrai dossier, sauvegarde dans $(Split-Path $BackupDir -Leaf)"
    if (-not $WhatIfOnly) {
      New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
      Move-Item $target (Join-Path $BackupDir $dir)
    }
  }
  else { Step "$dir : absent, creation de la jonction" }

  if (-not $WhatIfOnly) {
    New-Item -ItemType Junction -Path $target -Target $source | Out-Null
  }
}

# --- Fichiers rendus ------------------------------------------------------
$persoMd = if ($Perso) { Join-Path $Perso 'CLAUDE.md' } else { $null }
$persoComplet = if ($Perso) { Join-Path $Perso 'CLAUDE.complet.md' } else { $null }
$useComplet = $persoComplet -and (Test-Path $persoComplet)

function Resolve-PersoMarker([string] $Text) {
  <# Replaces each {{PERSO}} marker and the path tail following it with the normalized absolute path under $Perso. #>
  # Le marqueur et la suite du chemin partent ensemble : sinon seul le premier
  # separateur passe en Windows et la ligne rendue melange les deux formes.
  [regex]::Replace(
    $Text,
    '\{\{PERSO\}\}(?<tail>[\w./\[\]-]*)',
    { param($m) [System.IO.Path]::GetFullPath($Perso + $m.Groups['tail'].Value.Replace('/', [char]92)) }
  )
}

if ($useComplet) {
  $claudeMd = Resolve-PersoMarker (Get-Content $persoComplet -Raw)
}
else {
  $insert = ''
  if ($persoMd -and (Test-Path $persoMd)) {
    $insert = (Resolve-PersoMarker (Get-Content $persoMd -Raw)) + "`n"
  }
  $claudeMd = [regex]::Replace(
    (Get-Content (Join-Path $Repo 'CLAUDE.md') -Raw),
    '\{\{PERSO_CLAUDE_MD\}\}\r?\n(?:\r?\n)?',
    { param($m) $insert }
  )
}
if ($claudeMd.Contains('{{PERSO')) {
  throw "CLAUDE.md : un marqueur {{PERSO...}} survit au rendu, ~/.claude/CLAUDE.md n'est pas ecrit."
}
if ($useComplet) {
  Step "CLAUDE.md : remplace par le CLAUDE.complet.md du dossier perso"
  if (Test-Path $persoMd) {
    Step "CLAUDE.md : le CLAUDE.md du dossier perso est ignore, CLAUDE.complet.md le remplace"
  }
}
else { Step "CLAUDE.md : rendu, avec le CLAUDE.md du dossier perso s'il en a un" }
if (-not $WhatIfOnly) {
  Set-Content (Join-Path $ClaudeHome 'CLAUDE.md') $claudeMd -NoNewline -Encoding utf8
  Copy-Item (Join-Path $Repo 'CAVEMAN.md') (Join-Path $ClaudeHome 'CAVEMAN.md') -Force
}
Step "CAVEMAN.md : copie"

# --- settings.json --------------------------------------------------------
# On repart des reglages en place pour ne pas perdre les cles ecrites par le
# harness et que ce repo ne gere pas.
$settingsPath = Join-Path $ClaudeHome 'settings.json'
$merged = [ordered]@{}
if (Test-Path $settingsPath) {
  # Une seule copie, ecrasee a chaque passe : le dossier horodate est reserve
  # aux vrais dossiers deplaces, qui eux ne se recreent pas.
  if (-not $WhatIfOnly) {
    Copy-Item $settingsPath (Join-Path $ClaudeHome 'settings.json.prev') -Force
  }
  (Get-Content $settingsPath -Raw | ConvertFrom-Json).PSObject.Properties |
    ForEach-Object { $merged[$_.Name] = $_.Value }
}
if ($Perso) {
  Step "dossier perso : $Perso"
  if (-not $WhatIfOnly) { Set-Content $PersoMemo $Perso -Encoding utf8 }
}
$layers = @((Join-Path $Repo 'settings.base.json'), (Join-Path $Repo 'settings.windows.json'))
if ($Perso) { $layers += (Join-Path $Perso 'settings.json'), (Join-Path $Perso 'settings.windows.json') }
function ConvertTo-Canonical($Value) {
  <# Returns a copy of $Value whose object properties are sorted by name at every depth. #>
  if ($Value -is [System.Management.Automation.PSCustomObject]) {
    $sorted = [ordered]@{}
    foreach ($property in ($Value.PSObject.Properties | Sort-Object Name -CaseSensitive)) {
      $sorted[$property.Name] = ConvertTo-Canonical $property.Value
    }
    return $sorted
  }
  if ($Value -is [System.Collections.IDictionary]) {
    $sorted = [ordered]@{}
    foreach ($key in ($Value.Keys | Sort-Object -CaseSensitive)) {
      $sorted[$key] = ConvertTo-Canonical $Value[$key]
    }
    return $sorted
  }
  if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
    return , @($Value | ForEach-Object { ConvertTo-Canonical $_ })
  }
  return $Value
}
function Add-Unique($List, $Items) {
  <# Appends to $List each item of $Items not already held, comparing compact JSON with properties sorted, in order. #>
  foreach ($item in $Items) {
    $itemJson = ConvertTo-Json -InputObject (ConvertTo-Canonical $item) -Depth 20 -Compress
    $present = $false
    foreach ($existing in $List) {
      if ((ConvertTo-Json -InputObject (ConvertTo-Canonical $existing) -Depth 20 -Compress) -ceq $itemJson) { $present = $true; break }
    }
    if (-not $present) { [void]$List.Add($item) }
  }
}
function Expand-Markers($Text) {
  <# Replaces the {{CLAUDE_HOME}}, {{PYTHON}} and {{REPO}} markers in a layer's raw JSON text, backslashes escaped. #>
  $Text = $Text.Replace('{{CLAUDE_HOME}}', $ClaudeHome.Replace('\', '\\'))
  $Text = $Text.Replace('{{PYTHON}}', $Python.Replace('\', '\\'))
  # {{REPO}} : les dossiers de ~/.claude sont des jonctions vers ce depot ; sans
  # cette autorisation, une session ouverte ailleurs ne peut pas les suivre.
  return $Text.Replace('{{REPO}}', $Repo.Replace('\', '\\'))
}

function Test-OurHook($Hook) {
  <# Tells whether a hook's command, markers expanded, names a file under <ClaudeHome>\hooks; each rooted word or quoted string is normalized, '\' and '/' alike. #>
  $command = [string]$Hook.command
  $command = $command.Replace('{{CLAUDE_HOME}}', $ClaudeHome).Replace('{{PYTHON}}', $Python).Replace('{{REPO}}', $Repo)
  $sep = [IO.Path]::DirectorySeparatorChar
  $hooksDir = [IO.Path]::GetFullPath((Join-Path $ClaudeHome 'hooks').Replace('\', '/')).TrimEnd($sep) + $sep
  $comparison = if ($sep -eq '\') { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
  foreach ($match in [regex]::Matches($command, '"([^"]*)"|''([^'']*)''|(\S+)')) {
    $word = ($match.Groups[1].Value + $match.Groups[2].Value + $match.Groups[3].Value).Replace('\', '/')
    if ($word -match '^~/') { $word = $HOME.Replace('\', '/') + $word.Substring(1) }
    if (-not [IO.Path]::IsPathRooted($word)) { continue }
    if ([IO.Path]::GetFullPath($word).StartsWith($hooksDir, $comparison)) { return $true }
  }
  return $false
}
function Get-ForeignBlocks($Blocks) {
  <# Returns the blocks of an event stripped of our hooks, blocks left empty dropped. #>
  $kept = New-Object System.Collections.Generic.List[object]
  foreach ($block in @($Blocks)) {
    if ($block -isnot [System.Management.Automation.PSCustomObject]) { continue }
    $foreign = @(@($block.hooks) | Where-Object { $null -ne $_ -and -not (Test-OurHook $_) })
    if ($foreign.Count -eq 0) { continue }
    if ($foreign.Count -eq @($block.hooks).Count) { [void]$kept.Add($block); continue }
    $copy = [ordered]@{}
    foreach ($property in $block.PSObject.Properties) { $copy[$property.Name] = $property.Value }
    $copy['hooks'] = $foreign
    [void]$kept.Add([PSCustomObject]$copy)
  }
  return , $kept
}

# hooks et permissions se rebatissent a partir des couches : $null tant
# qu'aucune couche ne les definit, et l'existant est alors conserve. Des hooks
# existants, seuls ceux d'autres outils sont repris, apres ceux des couches.
$existingHooks = $merged['hooks']
$hooks = $null
$permissions = $null
foreach ($layer in $layers) {
  if (-not (Test-Path $layer)) { continue }
  (Expand-Markers (Get-Content $layer -Raw) | ConvertFrom-Json).PSObject.Properties |
    ForEach-Object {
      if ($_.Name -eq 'hooks') {
        if ($null -eq $hooks) { $hooks = [ordered]@{} }
        foreach ($hookEvent in $_.Value.PSObject.Properties) {
          if (-not $hooks.Contains($hookEvent.Name)) {
            $hooks[$hookEvent.Name] = New-Object System.Collections.Generic.List[object]
          }
          Add-Unique $hooks[$hookEvent.Name] $hookEvent.Value
        }
      } elseif ($_.Name -eq 'permissions') {
        if ($null -eq $permissions) { $permissions = [ordered]@{} }
        foreach ($entry in $_.Value.PSObject.Properties) {
          if ($entry.Value -is [array]) {
            if (-not ($permissions[$entry.Name] -is [System.Collections.Generic.List[object]])) {
              $permissions[$entry.Name] = New-Object System.Collections.Generic.List[object]
            }
            Add-Unique $permissions[$entry.Name] $entry.Value
          } else {
            $permissions[$entry.Name] = $entry.Value
          }
        }
      } elseif ($_.Name -eq 'env') {
        # env se fusionne cle par cle : un overlay ajoute une variable au socle,
        # il ne remplace pas le bloc entier.
        $envMerged = [ordered]@{}
        if ($merged['env']) {
          $merged['env'].PSObject.Properties | ForEach-Object { $envMerged[$_.Name] = $_.Value }
        }
        $_.Value.PSObject.Properties | ForEach-Object { $envMerged[$_.Name] = $_.Value }
        $merged['env'] = [PSCustomObject]$envMerged
      } else {
        $merged[$_.Name] = $_.Value
      }
    }
}
if ($null -ne $hooks) {
  if ($existingHooks -is [System.Management.Automation.PSCustomObject]) {
    foreach ($hookEvent in $existingHooks.PSObject.Properties) {
      $foreign = Get-ForeignBlocks $hookEvent.Value
      if ($foreign.Count -eq 0) { continue }
      if (-not $hooks.Contains($hookEvent.Name)) {
        $hooks[$hookEvent.Name] = New-Object System.Collections.Generic.List[object]
      }
      Add-Unique $hooks[$hookEvent.Name] $foreign
    }
  }
  $merged['hooks'] = $hooks
}
if ($null -ne $permissions) { $merged['permissions'] = $permissions }
$json = $merged | ConvertTo-Json -Depth 20
if ($json -cmatch '\{\{[A-Z_]+\}\}') {
  throw "settings.json : le marqueur $($Matches[0]) survit au rendu, ~/.claude/settings.json n'est pas ecrit."
}
Step "settings.json : base + overlay Windows + dossier perso, fusionnes sur l'existant"
if (-not $WhatIfOnly) { Set-Content $settingsPath $json -Encoding utf8 }

# --- Hooks git globaux -----------------------------------------------------
$hooksPath = (Join-Path $ClaudeHome 'git-hooks').Replace('\', '/')
$actuel = (& git config --global --get core.hooksPath 2>$null)
if (-not $actuel) {
  Step "git : core.hooksPath global -> $hooksPath"
  if (-not $WhatIfOnly) { & git config --global core.hooksPath $hooksPath }
}
elseif ($actuel.Replace('\', '/').TrimEnd('/') -eq $hooksPath) {
  Step "git : core.hooksPath global deja en place"
}
else {
  Write-Warning "core.hooksPath global vaut deja '$actuel' : laisse tel quel, le garde pre-push n'est pas actif."
}

Write-Host ""
Write-Host "Termine. Verifier les liens :"
Write-Host "  Get-Item ~\.claude\agents, ~\.claude\commands, ~\.claude\skills, ~\.claude\hooks, ~\.claude\git-hooks | Select-Object Name, LinkType, Target"
Write-Host "  git config --global --get core.hooksPath"
if (Test-Path $BackupDir) { Write-Host "Sauvegarde : $BackupDir" }
