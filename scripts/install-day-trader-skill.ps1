<#
Instala opcionalmente as 11 habilidades do projeto day-trader-skill no
Claude Code, apenas dentro deste repositorio. Nao integra corretoras, nao
modifica o DS Trader.exe e nao executa ferramentas de negociacao.

Uso na raiz do repositorio:
    powershell -NoProfile -File .\scripts\install-day-trader-skill.ps1
#>
param()
$ErrorActionPreference = 'Stop'
$repository = 'https://github.com/Jakeschincariol/day-trader-skill.git'
$expectedRevision = '3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$destination = Join-Path $root '.claude\skills'
$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ('ds-trader-skill-' + [guid]::NewGuid().ToString('N'))

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git nao encontrado. Instale o Git para Windows antes de continuar.'
}

try {
    & git clone $repository $temporary
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel baixar o day-trader-skill.' }
    # O branch remoto pode mudar; instalar sempre o commit fixado abaixo.
    & git -C $temporary checkout --detach $expectedRevision
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel selecionar a revisao fixada.' }
    $revision = (& git -C $temporary rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $revision -ne $expectedRevision) {
        throw 'A versao remota mudou desde a revisao. Instalacao interrompida para nova verificacao.'
    }
    $modules = @(Get-ChildItem -Path $temporary -Directory -Filter 'trader-*')
    if ($modules.Count -ne 11) { throw 'Esperadas 11 habilidades; estrutura remota inesperada.' }
    foreach ($module in $modules) {
        if (-not (Test-Path (Join-Path $module.FullName 'SKILL.md'))) {
            throw "Habilidade sem SKILL.md: $($module.Name)"
        }
        if (Test-Path (Join-Path $destination $module.Name)) {
            throw "Pasta ja existente: $($module.Name). Nada foi sobrescrito."
        }
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    foreach ($module in $modules) {
        Copy-Item -Path $module.FullName -Destination $destination -Recurse
    }
    Write-Host "Instaladas $($modules.Count) habilidades em $destination"
    Write-Host 'Reabra o Claude Code dentro deste projeto para acessar as habilidades.'
    Write-Host 'A leitura da IQ Option e o instalador DS Trader sao independentes.'
} finally {
    if (Test-Path $temporary) { Remove-Item -Path $temporary -Recurse -Force }
}
