# Hook PostToolUse — lint apres chaque ecriture, sur les projets AdonisJS seulement.

if (-not (Test-Path 'adonisrc.ts')) { exit 0 }

$out = & pnpm lint --quiet 2>&1
if ($LASTEXITCODE -ne 0) {
  [Console]::Error.WriteLine("Lint failed, corrige avant de continuer.`n$out")
  exit 2
}
exit 0
