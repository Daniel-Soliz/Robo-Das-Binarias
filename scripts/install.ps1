$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'DS-Trader'
$target = Join-Path $env:LOCALAPPDATA 'Programs\DS-Trader'
if (!(Test-Path (Join-Path $source 'DS-Trader.exe'))) { throw 'Extraia o ZIP completo antes de instalar.' }
New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item (Join-Path $source '*') $target -Recurse -Force
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'DS Trader.lnk'))
$link.TargetPath = Join-Path $target 'DS-Trader.exe'
$link.WorkingDirectory = $target
$link.Save()
Write-Host 'Instalado. Abra o atalho DS Trader na sua Área de Trabalho.'
Write-Host 'Para remover: exclua o atalho e a pasta' $target
Write-Host 'Históricos em LOCALAPPDATA\DS Trader são preservados.'
