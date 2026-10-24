# Relatório de testes — 24/10/2026

## Modo Automático por Ativo M5 — 24/10/2026

Adicionado motor puro `active_history` para estudar até 288 candles M5
fechados (24h), exigindo pelo menos 12h contínuas e bloqueando fonte
atrasada, futuro, lacunas e OHLC inconsistente. Cenários técnicos externos
apresentam confluências e fonte; **operação na IQ Option continua AGUARDAR**.
Ampliados de forma opcional os históricos REST de Binance, Kraken e Twelve
Data sem alterar limites do Radar anterior. `active_source` preserva
identidade exata do par, sem trocar USD por USDT ou inverter moeda.

`active_tracking` segue o par confirmado pelo OCR do Monitor em uma thread
separada; invalida estado em troca/OTC/perda de cabeçalho e descarta resposta
HTTP antiga por geração. Aplica validade local do fechamento mesmo entre
consultas. A chave Twelve Data entra só em memória, pela aba Radar.

**Verificação de 24/10/2026 nesta versão:** `pytest -q -rs` retornou
**216 aprovados, 1 ignorado** (recurso Windows `EnumWindows` indisponível
no Linux), em **3,01 s**. `compileall` e `git diff --check` saíram sem erro.
Os testes incluem competição entre troca de ativo e resposta atrasada,
invalidação ao expirar o candle, cabeçalhos consecutivos de frames reais
do pipeline em memória, incompatibilidade do período, e inclusão do módulo
`pytesseract` no ambiente empacotado.

Revisão independente identificou e foi corrigida uma aceitação indevida de
chave Kraken de ativo diferente (agora só aceita aliases explícitos), a
troca do seletor para M1/M15 mantendo cenário M5 (agora invalida) e a
esteira Windows usando `unittest discover` que não executava os testes
pytest (agora instala `requirements-test.txt` e roda a suíte completa).
O modo histórico puro também rejeita período diferente de M5.

**Teste real pontual (sem conta, sem ordens):** HTTPS Binance retornou
`BTC/USDT`, 288 candles M5 fechados, horizonte **24h**, idade **95s** e
status `ATUALIZADO`. O analisador retornou `AGUARDAR` no cenário histórico
observado e `AGUARDAR` operacional, sem inventar entrada.
Em execução adicional do `ActiveAssetTracking` com uma thread real e sem
API key, a fonte confirmou 288 candles fechados de BTC/USDT e o motor
publicou `AGUARDAR` (cenário) / `AGUARDAR` (operacional). Um teste OCR
com cabeçalho **sintético** `USD/JPY M5` passou pelo Tesseract local,
retornando o texto correto; **não é uma captura da IQ Option real**.

`scripts/gui_smoke.py` tentou iniciar o Tkinter mas recebeu
`TclError: no display name and no $DISPLAY environment variable` neste
Linux. Não há validação da interface gráfica nesta plataforma.

**Pendente:** reconhecimento OCR da IQ Option real, instalação de Tesseract
no Windows, validação do layout M5, sincronização corretora/fonte,
qualidade estatística de alertas, interface Tk e compilação de instalador
com esta versão. Forex sem chave não foi testado online e permanece sem fonte.

## Mercados públicos, Binance + TradingView — 24/10/2026

Implementados nesta branch: parser REST Binance Spot com 120 candles fechados
e validação estrita de `x=true`, ordem, intervalo, ativo e tempo UTC; worker
WebSocket público com fila limitada, erro explícito ao desconectar e reconexão;
integração do Radar com USD Kraken e USDT Binance sem equiparar moedas; e
painel HTML com widget oficial TradingView, B3/Forex/cripto e aviso B3 de
**15 minutos de atraso**. O botão abre um arquivo do próprio aplicativo no
navegador, não retorna candles do widget ao motor de sinais.

**Testes automatizados finais:** `.venv/bin/python -m pytest -q -rs` —
**192 aprovados, 1 ignorado** (integração `EnumWindows` exclusiva Windows),
em **2,82 s** neste host. `compileall` e `git diff --check` passaram.
O `gui_smoke.py` foi atualizado para verificar seis favoritos, o botão e
o asset empacotado, mas **não pôde executar neste Linux sem display**.

**Verificação real das fontes externas, 24/10/2026 (apenas pontual):**
`fetch_binance_history(BTC/USDT,1min)` consultou com êxito o endpoint
`data-api.binance.vision` por HTTPS, sem chave, retornando **120 candles
fechados**, último fechamento `2026-10-24T03:19:00Z`, idade 48 s e status
`ATUALIZADO` no instante da consulta. Uma conexão real ao endereço público
`wss://data-stream.binance.vision:443/stream?streams=btcusdt@kline_1m`
recebeu uma mensagem `BTCUSDT` com `k.x=true` (candle fechado). Esses
testes **não provam** funcionamento contínuo, disponibilidade da Binance no
computador do usuário, qualidade preditiva nem sincronização com IQ Option.

**Ainda pendente:** teste de 30 minutos do worker conectado, interação com
o painel TradingView num navegador Windows, smoke da GUI e build do instalador
com WebSocket e asset empacotado. A conexão da B3 é só visual e atrasada.

## Extensao sem chave e descoberta IQ Option — 24/10/2026

Incluidos testes de descoberta automatica segura de uma unica janela IQ
Option (duas observacoes, exclusao do proprio app, multiplos monitores,
ambiguidade, dimensoes), integracao com o evento de abertura na UI, Kraken
publico M1 com recusa de candle aberto e OHLC inconsistente, limite de 721
entradas (720 fechadas + atual), erros do fornecedor e radar sem credencial.

`python -m pytest -q -rs`: **171 aprovados, 1 ignorado** (API `EnumWindows`
exclusiva Windows) em **2,67 s**. `compileall` e `git diff --check` sem erro.

**Verificacao publica real:** consulta HTTPS sem autenticacao ao endpoint
`https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1` retornou
`error: []` e **721** entradas em 24/10/2026. O primeiro teste revelou um
limite de tamanho incorreto no parser (720); um teste de regressao o
reproduziu e foi corrigido. Consulta subsequente passou pelo proprio modulo
`fetch_public_crypto_candles` e devolveu **120 candles fechados**, fonte
"Kraken Spot publico", status `ATUALIZADO`, idade **4 segundos** no momento
do teste. O vies descritivo observado foi `ALTA`, mas nao e sinal nem prova
de eficacia preditiva. Sem custos, conta ou login. Esta validacao nao cobre
disponibilidade futura, Forex/B3, feed IQ Option ou tempo de tela.

**Ainda nao testado:** auto descoberta e recorte de janelas IQ Option
reais, reconexao grafica Windows 10/11, instalador atualizado, WebSocket
streaming e licenciamento de dados B3. A cobertura de Forex M1/M5/M15
exige fonte intradiaria apropriada e permanece sem cotacao na opcao publica.


## Etapa híbrida local — 23/10/2026 (branch `feature/ds-trader-hybrid`)

**Executado neste ambiente Linux:** `python -m pytest -q -rs` — **159 aprovados,
1 ignorado** (`EnumWindows` específico do Windows) em 2,67 s. `python -m
compileall -q ds_trader scripts tests_ds main.py` — sem erro. Os testes
abrangem agora identidade de ativo, troca com invalidação imediata,
quadros fora de ordem, rejeição de frames de mais de 2,5 s, classificação
Forex/cripto, candles fechados, HTTP/JSON 429 com pausa global do provedor,
erro de fonte, scanner parcial, cancelamento da consulta, remoção de
favoritos antigos e envelhecimento de uma análise no radar.

Benchmark de **processamento visual isolado** no arquivo de imagem gravada
`upload/01-110.jpg`, recorte `(100,90)-(1300,635)`, 100 repetições:
mediana **11,24 ms** e P95 **15,02 ms**; 31 corpos reconhecidos,
`visual_bias=INDEFINIDO`, `trading_signal=false`. Comparação histórica
anterior neste ambiente: mediana 11,08 ms e P95 16,18 ms. Variação
não comprova ganho de performance; o OCR e a rede não entram nesse benchmark.

`python scripts/gui_smoke.py` **não executou teste de interface** porque
`tk.Tk()` encontrou `TclError: no display name and no $DISPLAY environment
variable`. Trata-se de restrição deste host Linux; não se pode afirmar que
os novos controles Tk ou o instalador já foram testados no Windows.

**Ainda pendente:** OCR realmente reconhecendo pares na janela da IQ Option,
instalação/configuração do mecanismo OCR no Windows, feeds reais Twelve Data
com chave e plano do usuário, teste de limites/cobertura, duração e memória
durante 30 minutos, smoke do executável Windows e lançamento de release.
Até isso ocorrer, nenhuma hipótese por pixels será tratada como candle
comprovadamente fechado, operação, probabilidade de acerto ou lucro.

## Atualizacao — 22/10/2026 (captura de janela fixada, versao 1.4)

Nova escolha automatica da janela sob o recorte com exclusao do processo
DS Trader. Captura Windows Graphics Capture associada ao HWND, com recorte
relativo a janela, sem trocar de fonte caso outro aplicativo sobreponha.
Erros de dependencia, janela fechada/minimizada e quadros parados interrompem
a captura. Um recorte que nao caiba numa janela inteira e rejeitado.

`tests_ds/test_window_capture.py` cobre: ordem Z, exclusao de autocaptura,
recorte e escala, selecao rejeitada, stub de Windows Graphics Capture que
comprova uso do HWND em vez do desktop e ausencia de fallback silencioso.

**Ainda nao testado neste ambiente Linux:** janela real Chrome/IQ Option
obscurecida por outra no Windows, GPU/DPI especificos e conteudo protegido.
O build Windows testa empacotamento/interface; a prova de sobreposicao
real depende de teste manual no computador do usuario.

## Atualizacao — 21/10/2026 (ciclo de teste M1)

O ciclo cronologico isolado de `ds_trader/m1_cycle.py` ganhou testes em
`tests_ds/test_m1_cycle.py`: abertura e vencimento exatamente separados por
60s, preparacao antes da abertura, bloqueio de candle aberto/futuro, ausencia
de duplicacao, atraso, perda de ativo/M1/relogio, falta de comprovacao de
fechamento e comparacao ACERTO/ERRO/EMPATE sem retorno financeiro inventado.
O modulo `live_screen.assess` foi corrigido: remover o grupo mais a direita
nao autoriza `closed_confirmed=True`. O painel visual fica em AGUARDAR,
preservando LTA/LTB e padroes estimados.

Nao houve teste de sincronizacao/entrada real na IQ Option nem integracao
de feed de ticks verificados. A fonte Twelve Data atual nao fornece eventos
exatos de abertura e fechamento para esse ciclo; nao os fabrica.

## Executado neste ambiente

`python -m unittest discover -s tests_ds -v`: **23 testes aprovados** (Linux, Python do ambiente; núcleo sem dependências externas).

Cobertura: CSV válido/errado, duplicatas, ordem, lacunas, OHLC, fuso ausente, horários futuros, volume opcional, mercados separados, ausência de cotações; pivôs confirmados, alta/baixa, invalidação/prazo, igualdade de eventos em cada prefixo do histórico (sem uso de futuro), processamento repetido; ganho/perda/empate, payout variável/hipotético, entrada posterior, expiração inexata indeterminada, resultados não revelados antes do vencimento, divisão desenvolvimento/teste, simultaneidade; SQLite reaberto, backup e JSON/CSV; funcionamento com rede indisponível.

`python -m compileall -q ds_trader scripts tests_ds main.py`: sem erros.

## Windows e interface

A máquina local não oferece Windows nem sessão gráfica. **Nenhuma instalação manual Windows 10/11 foi executada localmente.**

Workflow `.github/workflows/testes.yml` prepara Python 3.11.9 x64 em Windows Server 2022, executa a suíte, constrói com PyInstaller e abre o **executável real** com `--smoke-test`. O teste cria janela Tk, desenha candles, avança reprodução, pausa, completa, reabre histórico e exporta. Só produz pacote se o teste passa. Foi adicionado um instalador Inno Setup que instala por usuário, cria atalhos na Área de Trabalho e no Menu Iniciar e contém desinstalador. O script também confere a instalação e a abertura do .exe instalado. A release é publicada automaticamente no GitHub somente após esses testes e verificação SHA-256. Evidência será o status da execução e `smoke-result.json` dentro do artifact. Até a execução concluir, build e GUI permanecem não verificados. Passar no Windows Server não substitui instalação/interação manual em Windows 10/11.

A suíte antiga `tests/` roda separadamente no trabalho `legacy`; não alegamos execução local dela (dependências antigas não instaladas aqui). O build antigo testava instalação simples por script. O novo build usa o instalador Inno Setup; sua execução e publicação ainda precisam ser verificadas no status da execução do GitHub Actions. A desinstalação manual não é testada.

A primeira execução Windows detectou uma leitura de JSON no teste sem encoding explícito. Corrigido para UTF-8; o exportador já gravava em UTF-8. O relatório final deve considerar a execução posterior à correção.

## Limitações que permanecem

- Sem conexão ao vivo, autenticação IQ Option, reconexão de fonte ativa ou IA externa: não aplicáveis os testes de falha desses serviços; apenas independência de rede foi testada.
- Sem dados reais de validação financeira; testes usam somente dados sintéticos. Nenhum índice de rentabilidade é evidência de vantagem de mercado.
- Uma cotação explícita de abertura por barra; sem ticks intrabar, interpolação, ordem real ou liquidação proprietária da corretora.
- Execuções indeterminadas não contam como zero; métricas de saldo representam apenas a parte determinável.
- Parâmetros não são calibrados. Repetir ajustes no teste contamina a avaliação. Wilson pressupõe independência.
- Arquivo completo é rejeitado se há falha; não há calendário de pregão, conversão de formatos livres ou reparo automático.
- Interface mostra últimos 90 candles revelados, sem zoom/arraste; reprodução individual por ativo/fonte/mercado/intervalo. Para comparar ativos, execute cada seleção e exporte seus relatórios.
- Histórico persiste; replay interrompido não retoma o cursor após reiniciar o aplicativo.
- Instalador Inno Setup com assistente gráfico e desinstalador, mas sem assinatura digital; não é MSI. Versão portátil e instalador simples antigo continuam disponíveis.
- Não houve avaliação de desempenho em arquivos grandes. Salvamento local ocorre a cada passo e contém o CSV original.

## Novo modo: Forex por API Twelve Data (v1.1, nao validado em servidor real)

O aplicativo agora possui aba `Forex em tempo real` que solicita chave de API em campo mascarado e consulta candles Forex por HTTPS. O feed de 1/5/15 min nao e streaming tick-a-tick. A chave e mantida somente na sessao e descartada ao desconectar; nao e gravada em SQLite ou CSV.

Foram adicionados testes unitarios offline em `tests_ds/test_forex_live.py`: parse estrito de OHLC UTC, par e intervalo, rejeicao de duplicatas e preços invalidos, descarte da vela ainda aberta, tratamento de lacunas, estados atrasados, indicador descritivo de tendencia, rejeicao de 429, verbosidade de erro que nao expõe chave e consulta somente ao endpoint GET /time_series. O smoke test verifica que a aba existe e que a API nao e acessada automaticamente.

**Ainda nao verificado:** chamada real a Twelve Data com credenciais validas, compatibilidade do plano do usuario, latencia efetiva ou release Windows atualizado. Confirmar no GitHub Actions que os testes das duas plataformas passaram e o EXE foi publicado antes de liberar o download.

## Evolução posterior — leitor visual de tela

Foram adicionados `tests_ds/test_live_screen.py` com sete testes unitários para geometria, configuração, imagem em branco e candles coloridos de alta/baixa. Eles verificam também que o modo visual não fornece preço de mercado nem sinal de ordens. O `scripts/gui_smoke.py` agora verifica a existência da aba e a ausência de captura automática.

**Status:** as alterações foram gravadas no GitHub, mas NÃO há evidência confirmada neste relatório de que o novo CI Windows tenha ficado verde ou que o instalador atualizado tenha sido publicado. A captura real de tela no Windows, com diferentes plataformas, resoluções e tema de cores, NÃO foi validada. Nenhuma alegação de acerto financeiro pode ser baseada no modo visual.

A fila de frames tem capacidade 1, descartando imagens antigas para reduzir atraso; a captura é executada em thread dedicada. Erros interrompem a captura com mensagem em tela. Não são enviados pixels ou credenciais para servidores por este modo. A leitura é aproximada, pode falhar em temas distintos, sobreposições, várias janelas, monitores e DPI.

## Motor de padroes e hipotese da proxima vela (v1.2)

Adicionados `ds_trader/next_candle.py` e `tests_ds/test_next_candle.py`:
pivos com confirmacao bilateral, LTA/LTB, engolfo, doji, hipotese CALL/PUT/
AGUARDAR e abstencao em amostras insuficientes. A aba da tela recusa recortes
geometricamente irregulares/curtos, desenha as linhas de tendencia estimadas
em copia da previa e mantem `trading_signal=False`: a hipotese nao e ordem
nem cotacao de mercado. A aba da API calcula o mesmo vies sobre candles
fechados, e cancela a hipotese se a barra estiver velha demais.

**Resultados de testes desta versao NAO confirmados neste documento.**
Exigir GitHub Actions completamente verde e testes manuais em Windows e no
grafico real. Ver [SINAIS](SINAIS.md) para criterios de aceite e riscos.

## Ciclo M1 causal: abertura e vencimento (2026-10-22)

O módulo `ds_trader/m1_cycle.py` agora exige uma fonte de quotes com timestamps
declarada `TIMESTAMPED_QUOTES`, confirmação individual de fechamento dos
candles (`confirmed_at`) antes da preparação e cotação de referência
observada na fronteira de abertura M1, da mesma fonte/ativo/período.
Só compara a referência de entrada ao preço de referência de vencimento
exatamente 60 segundos depois e se houver prova de fechamento.
O relógio com fuso e identidade do ativo/período devem permanecer válidos.

Cenários automatizados incluídos/atualizados em
`tests_ds/test_m1_cycle.py`: hipótese pendente e ativação na fronteira,
candle ainda aberto, timestamp ausente ou futuro, fonte sem comprovação,
período diferente de M1, histórico com lacuna, atraso de abertura,
preço do minuto anterior em vez do preço real de abertura,
vencimento anterior/incorreto, falha de sincronização, avaliação
somente após fechamento e ciclo duplicado. O smoke de GUI verifica
que a aba visual mostra o motivo de AGUARDAR e nenhuma entrada M1 registrada.

**Verificação nesta revisão:** os arquivos atualizados foram relidos
diretamente do GitHub e conferidas as condições essenciais de segurança,
a integração da interface e a presença dos testes. **A execução efetiva
da suíte Python e a compilação do EXE Windows ainda não foram confirmadas
neste ambiente**. O GitHub Actions executa os testes no push; somente
uma execução verde e validação local no Windows poderão comprovar
o instalador e o comportamento empacotado.

A tela IQ Option **não comprova** hora de fechamento, relógio oficial
ou preços de abertura/vencimento e, portanto, **não habilita** ciclos
M1 válidos. A Twelve Data devolve candles do seu fornecedor, não
preços/execuções da IQ Option; os dados não são fundidos automaticamente.
Nenhuma ordem ou lucro real foi testado/implementado.
