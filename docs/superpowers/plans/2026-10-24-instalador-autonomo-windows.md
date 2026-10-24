# Instalador autônomo Windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar fonte empacotável de DS Trader Windows com OCR embutido e Radar M5 inicial.

**Architecture:** Preservar o pipeline PyInstaller/Inno Setup. Um adaptador pequeno resolve Tesseract em ambiente congelado, e os dois pontos de OCR o consultam. O Radar existente já busca dados públicos em segundo plano.

**Tech Stack:** Python 3.11, Tkinter, PyInstaller, PowerShell, Inno Setup 6, pytest.

**Spec:** `docs/superpowers/specs/2026-10-24-instalador-autonomo-windows-design.md`

## Global Constraints

- Sem ordens reais nem uso de dados fictícios como atuais.
- Forex exige fonte autorizada e chave configurada; a instalação não a cria.
- Não remover dados em `%LOCALAPPDATA%\DS Trader`.
- Build deve falhar se Tesseract e `eng.traineddata` não estiverem incluídos.

## Review Focus

- Tesseract ausente no Windows: build interrompido.
- Runtime congelado sem caminho válido: não assumir ativo reconhecido.
- `eng.traineddata` ausente: build interrompido.
- Usuário sem API Forex: status SEM FONTE, sem cotações.
- Mudança de visualização inicial: demais páginas continuam acessíveis.

---

### Task 1: Preferências iniciais de mercado

**Files:** `ds_trader/dashboard_shell.py`, `ds_trader/market_radar_ui.py`, `scripts/gui_smoke.py`, `tests_ds/test_startup_defaults.py`.

**Interfaces:** `DashboardShell.mount(notebook, frames)` seleciona `radar`; `RadarTab.interval` começa em `5min`.

- [ ] Adicionar teste que exige Radar como página inicial e período M5.
- [ ] Executar teste e confirmar falha.
- [ ] Alterar seleção inicial e período.
- [ ] Executar teste; atualizar smoke Windows.

### Task 2: OCR autônomo do Windows

**Files:** `ds_trader/ocr_runtime.py`, `utils/ocr.py`, `ds_trader/live_screen.py`, `scripts/build.ps1`, `tests_ds/test_embedded_ocr.py`.

**Interfaces:** `configure_tesseract(pytesseract_module)` configura `tesseract_cmd` apenas se encontrar binário incluído; build instala/copia binário e idioma inglês.

- [ ] Criar testes que exijam caminho correto e build com recursos OCR.
- [ ] Executar testes e confirmar falha.
- [ ] Implementar resolução local e inclusão via PyInstaller.
- [ ] Executar testes e conferir que não existe fallback inseguro.

### Task 3: Conferência e entrega

**Files:** `README.md`, testes existentes, novo ZIP-fonte.

- [ ] Documentar uso do Setup, diferença entre dados públicos e IQ Option e testes Windows pendentes.
- [ ] Executar suíte completa, conferir sintaxe, integridade do ZIP e scripts de build.
- [ ] Entregar somente ZIP-fonte até que `DS-Trader-Setup.exe` seja efetivamente compilado e testado em Windows.
