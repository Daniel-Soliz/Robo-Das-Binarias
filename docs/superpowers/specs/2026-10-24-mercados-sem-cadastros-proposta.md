# Proposta de etapa 2 — Mercados globais sem varios logins

Data: 24/10/2026. **Proposta para aprovacao, nao funcionalidade implementada.**

## Problema

Daniel quer abrir o DS Trader junto da IQ Option, receber leitura visual
do ativo selecionado e observar Forex, cripto e B3 na parte inferior, com
origem identificada, baixa latencia e sem cadastrar uma API por mercado.

## Alternativas consideradas

1. **Scraping de TradingView / IQ Option**: aparente zero cadastro, mas
   frágil, possivelmente contrario aos termos, sem origem/sincronizacao
   verificavel; rejeitado como fonte de candles ou sinais.
2. **Uma API comercial para tudo**: dados estruturados, mas chave, custo,
   limites e licencas, especialmente para B3; fica como opcao para quem
   depois precisar de feed certificado.
3. **Painel TradingView oficial + dados publicos abertos por adaptador**:
   recomendado. Os widgets exibem seus proprios dados de Forex, cripto
   e B3 sem API criada pelo usuario. O motor analitico independente usa
   somente feeds que permitem acesso programatico (Kraken/Binance spot).

## Desenho recomendado

**Visualizacao (nao alimenta o motor):** incorporar widgets financeiros
oficiais do TradingView em um painel web controlado do app Windows.
Mostrar fonte e creditos originais. O TradingView informa Forex/cripto
em tempo real e B3 com atraso de 15 min, quando o simbolo for elegivel.
Verificar exibicao num Windows 10/11 real. **Nao** extrair dados de
widgets ou reclassificar B3 atrasada como ao vivo.

**Analise programatica de cripto:** usar Kraken publico (ja na etapa 1)
como fonte USD, ou adicionar adaptador Binance Spot public WebSocket:
`wss://data-stream.binance.vision:443`, canais `@kline_1m` etc.,
com evento `k.x == true` como marca de candle fechado, historico via
REST, reconexao com backoff e idade de fonte. Binance negocia por
exemplo `BTC/USDT`, que **nao e o mesmo par** de `BTC/USD`; apresentar
simbolo e bolsa exatos. Nunca inventar probabilidade, paridade ou
estado de ordem. Limitar universo observado e consumo de memoria.

**Forex intradiario:** manter Twelve Data (ou provedor autorizado), com
uma unica chave opcional; nunca substituir silenciosamente por PTAX diaria
ou cotacoes visuais do widget para gerar sinais M1.

**B3:** exibir informacoes atraves do widget oficial e rotular
`ATRASO 15 MIN` quando aplicavel; **sem analise automatica M1** ate
adquirir dados adequadamente autorizados. Consultar direitos de uso
antes de republicar/redistribuir valores ou criar scanner de sinais.

**Captura IQ Option:** continuar por HWND no Windows e OCR local da identidade,
com recorte central automatico apenas experimental. Se ativo, ciclo, DPI
ou horario nao forem confirmados: `AGUARDAR`, nunca enviar ordens.

## Validacao esperada (antes de chamar de concluido)

- Widget B3, Forex e cripto realmente visiveis, com atrasos e atribuicao.
- WebSocket recebe candles, rejeita `x == false`, reconecta corretamente e
  interrompe leituras em atraso.
- Latencia p50/p95, CPU/RAM e estado de rede medidos numa sessao Windows.
- Ausencia de vazamento de credenciais e de qualquer rotina de ordem real.
- Suite automatizada e teste manual no Windows antes de gerar instalador.

## Fontes primarias consultadas

- https://www.tradingview.com/widget-docs/faq/data/
- https://www.tradingview.com/blog/en/b3-data-available-in-tradingview-widgets-41743/
- https://www.tradingview.com/widget-docs/getting-started/
- https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md
- https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md
- https://docs.kraken.com/api/docs/rest-api/get-ohlc-data/
