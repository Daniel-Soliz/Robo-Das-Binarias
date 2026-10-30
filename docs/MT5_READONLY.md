# MT5 read-only — protótipo isolado

O arquivo ds_trader/mt5_readonly.py é um conector **experimental**, ainda **não conectado ao Radar ou à interface**. Ele chama MetaTrader5.initialize() (que pode iniciar o terminal instalado), exige terminal conectado e **conta demo**, e lê somente candles M1 fechados de até seis símbolos explicitamente configurados. Não envia ordens, não guarda credenciais e não acessa a IQ Option.

## Preparação no Windows

1. Instale o MetaTrader 5 oficial e faça login **manualmente uma vez** em uma conta demonstrativa. Mantenha o terminal configurado e conectado.
2. No Python 3.11 Windows, instale a biblioteca oficial com `python -m pip install MetaTrader5` (dependência opcional, não instalada no build principal).
3. No Python do projeto, use `from ds_trader.mt5_readonly import MT5ReadOnlyFeed`; depois `feed = MT5ReadOnlyFeed()`, `feed.connect()`, `feed.read_closed_m1("EUR/USD")`, `feed.close()`. Se necessário, passe `terminal_path` ao criar o feed.
4. Confira se os nomes de símbolos no terminal são exatamente EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD. Corretoras podem usar sufixos. Nesse caso, passe `symbols={"EUR/USD": "EURUSD.a", ...}` explicitamente; o programa não faz equivalências silenciosas.
5. Teste primeiro em conta demo, com relógio UTC sincronizado, 25+ candles M1 consecutivos e mercado aberto. Em falhas, mantenha AGUARDAR.

## Ainda pendente

- Integrar este conector ao Radar e à seleção de fontes, preservando os provedores existentes.
- Adicionar tratamento visual dos estados, reconexão e log sem dados de conta.
- Testar com terminal real no Windows, instalar e empacotar a dependência opcional.
- Comparar símbolo, fechamento, preço e fuso com IQ Option, sem assumir equivalência. Ativos OTC da IQ Option **não** podem ser substituídos por Forex spot MT5.
- Medir latência, estabilidade e, em teste separado fora da amostra, desempenho de hipóteses da próxima vela. Não há taxa de acerto demonstrada.

Os testes em tests_ds/test_mt5_readonly.py usam um MT5 falso; não verificam dados de mercado reais.
