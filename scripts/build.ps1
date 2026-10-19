# Build reproduzivel no Windows: tests -> PyInstaller -> GUI real -> Inno Setup -> instalacao real.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

try {
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias de build' }
python -m unittest discover -s tests_ds -v
if ($LASTEXITCODE -ne 0) { throw 'Testes do motor falharam' }

foreach ($folder in @('release', 'release-build')) {
    if (Test-Path $folder) { Remove-Item $folder -Recurse -Force }
}
Remove-Item smoke-result.json, smoke-error.txt -ErrorAction SilentlyContinue

python -m PyInstaller --noconfirm --clean --windowed --name DS-Trader main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller falhou' }
$exe = (Resolve-Path 'dist/DS-Trader/DS-Trader.exe').Path
$p = Start-Process -FilePath $exe -ArgumentList '--smoke-test' -WorkingDirectory (Get-Location).Path -Wait -PassThru
if ($p.ExitCode -ne 0 -or !(Test-Path smoke-result.json)) {
    throw 'O executavel real falhou no teste de GUI. Consulte smoke-error.txt'
}

# Pacote portatil, para quem preferir sem instalacao.
New-Item -ItemType Directory -Force -Path release | Out-Null
Copy-Item dist/DS-Trader release/DS-Trader -Recurse -Force
Copy-Item examples release/examples -Recurse -Force
Copy-Item docs release/docs -Recurse -Force
Copy-Item README.md release/README.md -Force
Copy-Item scripts/install.ps1 release/install.ps1 -Force
Copy-Item scripts/Instalar.cmd release/Instalar.cmd -Force
Copy-Item smoke-result.json release/smoke-result.json -Force
Compress-Archive -Path release/* -DestinationPath DS-Trader-Windows-x64.zip -Force
$portableHash = (Get-FileHash DS-Trader-Windows-x64.zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$portableHash  DS-Trader-Windows-x64.zip" | Set-Content DS-Trader-Windows-x64.sha256.txt -Encoding Ascii

# Inno Setup cria o assistente tradicional, desinstalador e atalho do desktop.
$candidateDirs = @()
if (${env:ProgramFiles(x86)}) { $candidateDirs += (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6') }
if ($env:ProgramFiles) { $candidateDirs += (Join-Path $env:ProgramFiles 'Inno Setup 6') }
$command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$iscc = if ($command) { $command.Source } else { $null }
foreach ($dir in $candidateDirs) {
    $found = Join-Path $dir 'ISCC.exe'
    if (Test-Path $found) { $iscc = $found; break }
}
if (!$iscc) {
    Write-Host 'Instalando compilador Inno Setup...'
    choco install innosetup --version=6.4.3 --yes --no-progress
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar Inno Setup 6.4.3. Consulte logs do Chocolatey.' }
    foreach ($dir in $candidateDirs) {
        $found = Join-Path $dir 'ISCC.exe'
        if (Test-Path $found) { $iscc = $found; break }
    }
}
if (!$iscc) { throw 'Compilador ISCC.exe ausente; nao e seguro oferecer instalador.' }
$outdir = (Join-Path (Get-Location).Path 'release-build')
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
& $iscc "/O$outdir" (Join-Path (Get-Location).Path 'scripts/DS-Trader.iss')
if ($LASTEXITCODE -ne 0) { throw "Erro ao compilar instalador Inno Setup (codigo $LASTEXITCODE)" }
$installer = (Resolve-Path 'release-build/DS-Trader-Setup.exe').Path

# Validacao do fluxo que o usuario vera: instalar, atalho e iniciar o instalado.
$p = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-') -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "O instalador retornou erro $($p.ExitCode)" }
$installed = Join-Path $env:LOCALAPPDATA 'Programs\DS Trader\DS-Trader.exe'
if (!(Test-Path $installed)) { throw "Executavel instalado nao encontrado: $installed" }
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'DS Trader.lnk'
if (!(Test-Path $desktopShortcut)) { throw 'Atalho de Area de Trabalho nao foi criado' }
$p = Start-Process -FilePath $installed -ArgumentList '--smoke-test' -WorkingDirectory (Get-Location).Path -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Aplicativo instalado falhou no teste real' }
if (!(Test-Path smoke-result.json)) { throw 'Relatorio do teste GUI ausente' }
Copy-Item smoke-result.json release-build/smoke-result.json -Force

$installerHash = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
"$installerHash  DS-Trader-Setup.exe" | Set-Content DS-Trader-Setup.sha256.txt -Encoding Ascii
Write-Host 'BUILD CONCLUIDO: DS-Trader-Setup.exe + pacote portatil + SHA256'

} catch {
    $details = ($_ | Out-String) + [Environment]::NewLine + $_.ScriptStackTrace
    $details | Set-Content -Path build-error.txt -Encoding UTF8
    Write-Error "BUILD FALHOU. Detalhes gravados em build-error.txt: $details" -ErrorAction Continue
    exit 1
}
