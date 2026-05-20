# Crée un raccourci FacturePro sur le Bureau
# Double-cliquez une seule fois pour installer

$exePath     = Join-Path $PSScriptRoot "FacturePro.exe"
$raccourci   = Join-Path ([Environment]::GetFolderPath("Desktop")) "FacturePro.lnk"

if (-Not (Test-Path $exePath)) {
    Write-Host "❌ FacturePro.exe introuvable dans ce dossier." -ForegroundColor Red
    Read-Host "Appuyez sur Entrée pour quitter"
    exit
}

$shell = New-Object -ComObject WScript.Shell
$lnk   = $shell.CreateShortcut($raccourci)
$lnk.TargetPath       = $exePath
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.Description      = "Logiciel de Facturation FacturePro"
$lnk.IconLocation     = "$exePath,0"
$lnk.Save()

Write-Host "✅ Raccourci créé sur le Bureau : $raccourci" -ForegroundColor Green
Read-Host "Appuyez sur Entrée pour fermer"
