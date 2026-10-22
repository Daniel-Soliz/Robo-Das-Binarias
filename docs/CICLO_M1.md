# Ciclo de estudo M1 com fronteiras temporais verificáveis

**Status:** motor de testes implementado em `ds_trader/m1_cycle.py`. Sem
adaptador autorizado da IQ Option para quotes de abertura/vencimento. Portanto
a aba **Tela ao vivo** permanece em **AGUARDAR** para entradas verificadas.
Isto não é automação de ordens.

## Regra cronológica (exemplo fictício UTC)

- **12:34:00**: termina o último candle com fechamento verificável usado
  no contexto; a vela **12:34:00–12:35:00** está em formação.
- **12:34:59**: motor pode preparar hipótese **pendente** para o candle
  **12:35:00–12:36:00**, usando apenas 25+ candles fechados, contínuos,
  com seus horários de confirmação anteriores à preparação. Não pode usar
  o fechamento do candle em formação de 12:34, que ainda não existe.
- **12:35:00**: até que seja observada uma cotação efetiva da fonte no
  instante de abertura 12:35:00, o estado visível é **AGUARDAR**, sem
  entrada válida. Quando a fonte fornece `M1Price(kind="OPEN")` na fronteira
  exata com horário auditável e atraso máximo de 1 segundo, ativa apenas
  uma **referência de entrada de estudo**; nunca uma operação executada.
- **12:36:00**: somente após `M1Price(kind="CLOSE")` com
  `closed_confirmed=True`, evento da fonte exatamente no vencimento
  12:36:00 e observação com até 2 segundos de atraso, a referência da
  entrada pode ser comparada com a referência do fechamento.
  O registro contém ACERTO/ERRO/EMPATE *apenas* do movimento de referência;
  não calcula payout, execução ou lucro.

O candle mais recente fechado **no mesmo minuto em que o alvo abre** só
estaria disponível ao abrir o alvo; não pode servir para uma decisão
prévia. Por isso a máquina escolhe alvo um minuto depois do fechamento
mais recente já conhecido.

## Pré-condições obrigatórias

- Identidade do ativo, fonte e timeframe M1 confirmada externamente.
- Relógio UTC com fuso e sincronização confiável declarada pelo adaptador.
- Pelo menos 25 candles sequenciais M1, sem lacunas, com OHLC válidos,
  `closed_confirmed=True` e `confirmed_at` verificável
  entre o fim de cada candle e o instante de análise.
- Adaptador de quotes identificável com
  `source_kind="TIMESTAMPED_QUOTES"`; essa declaração exige evidências
  próprias da fonte. Não deve ser preenchida automaticamente pela imagem.
- Na abertura e no vencimento: preços reais **observados na fonte**,
  `event_at` igual ao instante da fronteira, `observed_at` no intervalo
  de atraso permitido, origem/ativo/período coerentes, relógio e cotação
  confirmados. OHLC.open/close de um CSV não são substitutos desse quote.
- Sincronização perdida, atraso, hora sem fuso, candle aberto,
  quote errado, duplicação ou falta de provas: **AGUARDAR**, sem registro
  de entrada válida ou acerto.
- Um mesmo minuto não é processado duas vezes durante a sessão.

## Separação de fontes

A captura WGC/mss vê **pixels**, não comprova ativo, horário de fechamento
nem preço recebido/executado pela IQ Option. Por isso não alimenta
`M1History` nem `M1Price` e chama apenas `block_visual`.
A API Twelve Data devolve candles OHLC agregados, que podem ter preços
diferentes da IQ Option e não confirmam execução, abertura ou vencimento
preciso na corretora; o app não os mistura silenciosamente com o ciclo IQ.

A análise visual continua exibindo padrões de candles, suporte/resistência
e LTA/LTB educacionais, sem afirmar entrada para a próxima vela.

## Verificação

`python -m unittest tests_ds.test_m1_cycle -v` cobre preparação,
fronteira, ativação, fechamento, atraso, falta de prova, quotes trocados,
periodicidade, lacunas, sincronização, bloqueio da tela e nenhuma duplicação.
`python -m unittest discover -s tests_ds -v` executa a suíte geral.
O workflow CI constrói o Windows apenas se os testes anteriores passarem.

**Ainda exige validação independente:** não há integração autorizada da
fonte IQ para timestamps/preços exatos nem comprovação de resultados
financeiros. Os testes usam dados sintéticos e NÃO provam vantagem estatística
em opções binárias.
