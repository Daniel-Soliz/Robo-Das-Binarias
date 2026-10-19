$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências' }
python -m unittest discover -s tests_ds -v
if ($LASTEXITCODE -ne 0) { throw 'Testes falharam' }
python -m PyInstaller --noconfirm --clean --windowed --name DS-Trader main.py
if ($LASTEXITCODE -ne 0) { throw 'Build falhou' }
New-Item -ItemType Directory -Force -Path release | Out-Null
Copy-Item dist/DS-Trader release/DS-Trader -Recurse -Force
Copy-Item examples release/examples -Recurse -Force
Copy-Item docs release/docs -Recurse -Force
Copy-Item README.md release/README.md -Force
Copy-Item scripts/install.ps1 release/install.ps1 -Force
Copy-Item scripts/Instalar.cmd release/Instalar.cmd -Force
$p = Start-Process -FilePath 'dist/DS-Trader/DS-Trader.exe' -ArgumentList '--smoke-test' -Wait -PassThru
if ($p.ExitCode -ne 0 -or !(Test-Path smoke-result.json)) { throw 'Smoke test do executável falhou' }
& ./release/install.ps1
$installed = Join-Path $env:LOCALAPPDATA 'Programs/DS-Trader/DS-Trader.exe'
$p = Start-Process -FilePath $installed -ArgumentList '--smoke-test' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Aplicativo instalado falhou' }
if (!(Test-Path (Join-Path ([Environment]::GetFolderPath('Desktop')) 'DS Trader.lnk'))) { throw 'Atalho não criado' }
Copy-Item smoke-result.json release/smoke-result.json
Compress-Archive -Path release/* -DestinationPath DS-Trader-Windows-x64.zip -Force
Get-FileHash DS-Trader-Windows-x64.zip -Algorithm SHA256 | Format-List | Out-File DS-Trader-Windows-x64.sha256.txt
