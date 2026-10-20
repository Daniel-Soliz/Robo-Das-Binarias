# Auditoria técnica — DS Trader (19/10/2026)

## Escopo revisado
- **Arquitetura histórica:** `ds_trader/data.py`, `strategy.py`, `simulation.py`, `storage.py` e `ui.py`. Preservado motor CSV causal e relatórios; não mesclar cotações de tela com liquidações históricas.
- **Legado:** `data_sources/screen_source.py`, `ui/calibration.py`, `utils/ocr.py`. Captura antiga baseada em OpenCV/Tesseract, com identificação por OCR e OHLC relativos sem preços/instantes comprovados; não estava integrada ao DS Trader desktop.
- **Empacotamento:** `scripts/build.ps1`, `scripts/DS-Trader.iss`, `.github/workflows/testes.yml`, `index.html`. Existe assistente Inno Setup, atalho na área de trabalho e botão ligado aos assets da última release. A página HTML publicar não significa que o EXE foi gerado.

## Alterações implementadas
1. `ds_trader/live_screen.py`: região com limites, captura mss em thread a cada ~1,2 s, fila de tamanho 1 (descarta frame antigo), detecção simples de corpos verde/vermelho e avaliação de alta/baixa visual relativa.
2. `ds_trader/live_ui.py`: guia `Tela ao vivo`, seleção de área por arraste (Esc cancela), iniciar/parar, imagem de prévia e explicação; nenhum acesso automático à tela sem clicar.
3. `ds_trader/ui.py`: integração isolada do modo visual, encerramento da thread ao fechar, tentativa de alinhamento de coordenadas em Windows com DPI.
4. `requirements-runtime.txt`: versões fixadas `mss==9.0.2` e `Pillow==11.0.0`; build e CI passam a instalá-las e empacotá-las.
5. `tests_ds/test_live_screen.py`: testes de áreas válidas, limite de atualização, imagem sem velas, velas sintéticas de alta e baixa, não emissão de cotação/ordem, simulação do worker e da prévia.
6. `scripts/gui_smoke.py`: valida que a interface contém a guia e não inicia captura sem consentimento.
7. Documentação e página de apresentação atualizadas, distinguindo claramente leitura visual de preços oficiais da corretora.

## Bloqueios que impedem dizer "pronto"
- A captura do GitHub Actions enviada pelo usuário mostra a execução do aplicativo em **vermelho**; o registro da falha (job e log) ainda não foi disponibilizado a esta análise. **Causa exata não comprovada.** Ajustar código no escuro não comprova correção.
- Compilação e execução reais do novo instalador no Windows 10/11, criação do atalho e execução via ícone **ainda não confirmadas**. Somente uma execução completa verde do trabalho Windows com `DS-Trader-Setup.exe` publicado nos assets pode liberar o download.
- DPI em monitores com diferentes escalas, captura com gráficos reais, temas/cores variados e janelas cobrindo o gráfico requerem teste manual. Pode haver falso negativo ou falso padrão.
- Sistema não reconhece preços/tempo de expiração, login, ativo ou payout através da captura visual. Não transforma pixels em cotação de mercado nem em performance histórica. Não há indicação operacional CALL/PUT, clique automático, envio de ordens ou promessa de rentabilidade.
- Instalador sem assinatura digital: SmartScreen/Defender pode alertar; não orientar desativar proteções.

## Critérios de aceite (antes de anunciar release)
1. `python -m unittest discover -s tests_ds -v` passa em Linux e Windows.
2. PyInstaller Windows constrói `DS-Trader.exe`, teste `--smoke-test` passa e grava `smoke-result.json`.
3. Inno Setup gera `DS-Trader-Setup.exe`; instalação silenciosa de CI cria o atalho e o aplicativo instalado passa no `--smoke-test`.
4. SHA-256 do setup e do ZIP confere com os artefatos, e a release os publica.
5. Em Windows 10/11 real, usar instalador pela interface gráfica, abrir pelo atalho, carregar demo CSV, importar dados reais permitidos, exportar e desinstalar.
6. Para a tela ao vivo: escolher região, verificar prévia, cobrir/descobrir gráfico, mudar zoom/tema, pressionar parar e fechar. Se a leitura for ambígua, apresentar insuficiente em vez de preço ou sinal inventado.

## Próximas melhorias sujeitas a comprovação
- Testes de detecção com gravações ou imagens consentidas de gráficos reais, várias resoluções e cores, medindo falsos positivos/negativos.
- Para decisões vinculadas a uma operação, usar **fonte autorizada** de ticks com timestamps, preço de entrada/saída, expiração e payout; não inferir liquidação pela posição dos pixels.
- Estudo de zonas e alertas visuais não operacionais após validação do reconhecimento; nenhuma automação de ordens.

## Extensao v1.1 — dados Forex de fornecedor externo

- **Novo requisito de produto:** analisar pares fiat Forex durante sessao regular sem usar capturas de tela.
- **Provedor inicial:** Twelve Data Forex `GET /time_series`, HTTPS, autenticacao por chave criada pelo usuario, `timezone=UTC`, `1min/5min/15min`. A chave NAO e enviada no chat nem persistida no SQLite ou nos relatorios. A API exige chave, internet e permissao do plano; pode cobrar. A requisicao do provedor inclui chave na URL conforme documentacao, por isso pode ser visivel ao provedor e infraestrutura HTTP.
- **Analise:** candles fechados, validacao de OHLC, intervalo, duplicatas, futuro, lacunas, frescor, tendencia descritiva SMA9/SMA21 e pivos confirmados. A regra da sessao NY domingo 17h05 a sexta 16h59 e apenas referencia de horario Forex, sujeita a feriados e diferencas da fonte. Fora do horario, dados atrasados e lacunas nao sao classificados como tendencia de mercado atual.
- **Limites:** atualizacao minima a cada 60 s; padrao 120 s, custo estimado ate 720 consultas/dia para um par continuamente, sujeito as regras reais do fornecedor. NAO e streaming de ticks. Sem credenciais o app nao acessa a fonte; nao inventa preco em modo offline. Precos agregados da Twelve Data podem diferir dos precos/OTC da IQ Option; nao ha integracao de conta/ordens/payout.
- **Arquivos:** `ds_trader/forex_live.py`, `ds_trader/forex_ui.py`, `tests_ds/test_forex_live.py`; `requirements-runtime.txt` inclui `tzdata` para fusos IANA no Windows.
- **Validacao exigida:** conferir CI Windows/Linux verde para novo commit, instalador 1.1 com `forex_tab` no smoke-test, obtencao de chave valida da Twelve Data de acordo com seu plano (NAO compartilhar em chat), teste manual com varias moedas e periodos. Nao alegar leitura real validada antes de testar com provedor em mercado aberto.

Referencias: https://twelvedata.com/docs ; https://support.twelvedata.com/en/articles/12520817-forex-api-v2 ; https://www.oanda.com/us-en/trading/hours-of-operation/
