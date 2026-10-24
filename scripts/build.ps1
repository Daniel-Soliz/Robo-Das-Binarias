# Build reproduzivel no Windows: tests -> PyInstaller -> GUI real -> Inno Setup -> instalacao real.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

# Start-Process -Wait sem limite escondia janelas de erro e podia manter o
# trabalho Windows amarelo indefinidamente. Todas as etapas GUI têm watchdog.
function Invoke-CheckedProcess {
    param(
        [string] $FilePath,
        [string[]] $Arguments,
        [int] $TimeoutSeconds,
        [string] $Description
    )
    Write-Host "::group::$Description"
    Write-Host "Iniciando: $Description; tempo maximo $TimeoutSeconds segundos"
    $proc = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory (Get-Location).Path -PassThru
    try {
        $finished = $proc.WaitForExit($TimeoutSeconds * 1000)
        if (-not $finished) {
            try { $proc.Kill($true) } catch {
                try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch { }
            }
            throw "TIMEOUT: $Description nao terminou em $TimeoutSeconds segundos. Consulte smoke-error.txt e build-error.txt."
        }
        $proc.Refresh()
        if ($proc.ExitCode -ne 0) {
            throw "FALHA: $Description retornou codigo $($proc.ExitCode). Consulte smoke-error.txt e build-error.txt."
        }
    } finally {
        $proc.Dispose()
        Write-Host "::endgroup::"
    }
}

try {
Write-Host 'FASE 1/8: instalar dependencias de build'
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias de build' }
Write-Host 'FASE 2/8: instalar dependencias de captura'
python -m pip install -r requirements-runtime.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias da captura de tela' }
python -m pip install -r requirements-test.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar o executor de testes' }
Write-Host 'FASE 3/8: testar modulos e motor'
python -m pytest -q -rs
if ($LASTEXITCODE -ne 0) { throw 'Testes do motor falharam' }

# O executavel OCR deve acompanhar o aplicativo; pytesseract sozinho nao le texto.
# Procurar primeiro a instalacao existente da maquina de build.
$tesseractCandidates = @()
if ($env:ProgramFiles) { $tesseractCandidates += (Join-Path $env:ProgramFiles 'Tesseract-OCR') }
if (${env:ProgramFiles(x86)}) { $tesseractCandidates += (Join-Path ${env:ProgramFiles(x86)} 'Tesseract-OCR') }
$ocrCommand = Get-Command tesseract.exe -ErrorAction SilentlyContinue
if ($ocrCommand) { $tesseractCandidates += (Split-Path $ocrCommand.Source) }
$tesseractDir = $tesseractCandidates | Where-Object {
    (Test-Path (Join-Path $_ 'tesseract.exe')) -and
    (Test-Path (Join-Path $_ 'tessdata/eng.traineddata'))
} | Select-Object -First 1
if (!$tesseractDir) {
    Write-Host 'Instalando OCR somente na maquina de build...'
    choco install tesseract --yes --no-progress --limit-output
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar Tesseract na maquina de build' }
    $tesseractDir = $tesseractCandidates | Where-Object {
        (Test-Path (Join-Path $_ 'tesseract.exe')) -and
        (Test-Path (Join-Path $_ 'tessdata/eng.traineddata'))
    } | Select-Object -First 1
}
if (!$tesseractDir) { throw 'OCR incompleto: tesseract.exe ou eng.traineddata ausentes; instalador bloqueado' }
$ocrData = "$tesseractDir;tesseract"

foreach ($folder in @('release', 'release-build')) {
    if (Test-Path $folder) { Remove-Item $folder -Recurse -Force }
}
Remove-Item smoke-result.json, smoke-error.txt -ErrorAction SilentlyContinue

Write-Host 'FASE 4/8: compilar PyInstaller'
python -m PyInstaller --noconfirm --clean --windowed --name DS-Trader --add-data 'ds_trader/assets/mercados_globais.html;ds_trader/assets' --add-data $ocrData --collect-submodules websockets --collect-submodules pytesseract main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller falhou' }
$exe = (Resolve-Path 'dist/DS-Trader/DS-Trader.exe').Path
$ocrExe = (Resolve-Path 'dist/DS-Trader/_internal/tesseract/tesseract.exe').Path
if (!(Test-Path 'dist/DS-Trader/_internal/tesseract/tessdata/eng.traineddata')) {
    throw 'PyInstaller nao incluiu idioma ingles do OCR; instalador bloqueado'
}
Invoke-CheckedProcess -FilePath $ocrExe -Arguments @('--version') -TimeoutSeconds 30 -Description 'OCR embutido no aplicativo'
Write-Host 'FASE 5/8: teste GUI do EXE com watchdog'
Invoke-CheckedProcess -FilePath $exe -Arguments @('--smoke-test') -TimeoutSeconds 180 -Description 'Smoke teste GUI PyInstaller'
if (!(Test-Path smoke-result.json)) {
    throw 'O executavel nao gerou smoke-result.json. Consulte smoke-error.txt'
}

# Pacote portatil, para quem preferir sem instalacao.
Write-Host 'FASE 6/8: criar ZIP portatil'
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
Write-Host 'FASE 7/8: compilar instalador Inno Setup'
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
Write-Host 'FASE 8/8: instalar e testar aplicacao final'
Invoke-CheckedProcess -FilePath $installer -Arguments @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-') -TimeoutSeconds 300 -Description 'Instalacao silenciosa Windows'
$installed = Join-Path $env:LOCALAPPDATA 'Programs\DS Trader\DS-Trader.exe'
if (!(Test-Path $installed)) { throw "Executavel instalado nao encontrado: $installed" }
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'DS Trader.lnk'
if (!(Test-Path $desktopShortcut)) { throw 'Atalho de Area de Trabalho nao foi criado' }
Invoke-CheckedProcess -FilePath $installed -Arguments @('--smoke-test') -TimeoutSeconds 180 -Description 'Smoke teste EXE instalado'
if (!(Test-Path smoke-result.json)) { throw 'Relatorio do teste GUI ausente' }
Copy-Item smoke-result.json release-build/smoke-result.json -Force

$installerHash = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
"$installerHash  DS-Trader-Setup.exe" | Set-Content DS-Trader-Setup.sha256.txt -Encoding Ascii
Write-Host 'BUILD CONCLUIDO: DS-Trader-Setup.exe + pacote portatil + SHA256'

} catch {
    if (Test-Path smoke-error.txt) {
        Write-Host 'LOG DE ERRO DO EXECUTAVEL:'
        Get-Content smoke-error.txt | Select-Object -Last 90 | ForEach-Object { Write-Host $_ }
    }
    $details = ($_ | Out-String) + [Environment]::NewLine + $_.ScriptStackTrace
    $details | Set-Content -Path build-error.txt -Encoding UTF8
    Write-Error "BUILD FALHOU. Detalhes gravados em build-error.txt: $details" -ErrorAction Continue
    exit 1
}
