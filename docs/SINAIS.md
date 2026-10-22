# DS Trader 1.2 — leitura de padroes e hipotese da proxima vela

**ESTADO:** implementacao experimental no repositorio. Qualquer compilacao ou instalador
precisa passar no GitHub Actions e ser testado manualmente no Windows. Os testes
sinteticos nao validam estrategia financeira.

## O que significa CALL, PUT ou AGUARDAR

- **CALL — HIPOTESE:** confluencia de elementos observados favorece a continuidade
  ou a reversao para cima, sob regras programadas. NAO e instrucao de comprar.
- **PUT — HIPOTESE:** confluencia favorece a baixa. NAO e instrucao de vender.
- **AGUARDAR:** contexto incompleto, indecisao, suporte/resistencia oposta proxima,
  leitura irregular, dados velhos ou falta de fechamento confirmavel.

Nunca exibimos "chance de ganhar 90%" porque nenhum percentual foi calibrado
ou validado em amostra financeira independente. Nao existe martingale,
autoclique, login na corretora nem envio de ordens.

## Regras implementadas em `ds_trader/next_candle.py`

Usa **pelo menos 25 candles** e avalia apenas a parte fornecida como fechada:

1. **Direcao:** media simples dos ultimos 9 e 21 fechamentos com limite baseado na
   amplitude media dos 14 candles. Tendencia de alta, baixa ou indefinida.
2. **Pivos confirmados:** topo tem maxima estritamente acima dos 2 candles
   anteriores e 2 posteriores; fundo usa minima estritamente menor. Nunca
   usar velas futuras ainda nao fechadas.
3. **Suporte/resistencia:** ultimo pivo inferior/superior ao fechamento atual,
   sem desenhar nivel sem pivo comprovado.
4. **LTA:** uniao de dois ultimos fundos ascendentes, com 3 candles de distancia
   e confirmacao a direita; **LTB:** dois ultimos topos descendentes. Descartar
   linhas com ultimo pivo antigo demais.
5. **Padroes do ultimo candle:** engolfo de alta/baixa, doji, martelo (pavio
   inferior e corpo menor), pavio superior longo e inside bar. Definicoes
   simplificadas de engenharia, NAO equivalentes a todas as heuristicas TA-Lib.
6. **Confluencia:** tendencia, linhas, proximidade de suporte/resistencia e
   padroes somam evidencias. Se a direcao contraria tiver evidencias relevantes,
   se houver resistencia/suporte opostos muito proximos ou houver doji/inside bar,
   mostrar AGUARDAR. Sem ao menos 3 pontos e diferenca >=2, AGUARDAR.

Os limiares sao **hipoteses de desenvolvimento**, nao otimizacoes comprovadas.
O motor explica quais regras foram atendidas. Um padrao isolado nao prova
reversao/continuacao.

Referencias de definicoes:
- https://ta-lib.org/functions/cdlengulfing.html
- https://ta-lib.org/functions/cdldoji.html
- https://ta-lib.org/functions/cdlhammer
- https://cmtassociation.org/wp-content/uploads/2025/12/CMT-PROGRAM-GUIDE-2026-1.pdf

## Fonte 1 — Tela ao vivo (IQ Option e outros graficos)

1. Abra um grafico de candles e deixe visivel, preferencialmente em uma area
   separada do DS Trader ou outro monitor.
2. Clique `Tela ao vivo → Selecionar area do grafico`. Selecione somente
   a regiao que contem os candles, **sem menus, botoes CALL/PUT, dinheiro,
   conta ou outras informacoes pessoais**.
3. Clique `Iniciar monitoramento`. O app le pixels locais a cada 1,2 s;
   exige pelo menos **26 objetos** consistentes em espacamento e descarta
   o grupo mais a direita (que pode ser vela em formacao).
4. Aguarda pelo menos **3 quadros consecutivos geometricamente estaveis**;
   ao alterar recorte, escala ou quantidade detectada, mostra AGUARDAR de novo.
5. Exibe **AGUARDAR** por falta de prova temporal, mas preserva a descricao
   de padroes e linhas LTA/LTB na previa quando reconhecidas.
6. Clique `Parar`. Imagens nao sao gravadas ou transmitidas.

**Limite critico:** nao existe comprovacao do instante exato em que a vela da
IQ Option fecha; a tela e apenas um desenho. Rolagem, zoom, cores, temas,
indicadores, sobreposicoes, OTC e cotações proprietarias podem produzir
falso padrao. O sistema nao verifica a expiração nem determina o proximo
instante de entrada na corretora. **Nao opere apenas pelo vies visual.**
Antes de depender de uma hipotese de proxima vela e necessario integrar dados
e relogio confiaveis da fonte.

## Fonte 2 — Forex em tempo real por API

A aba `Forex em tempo real` usa Twelve Data, com chave e plano do usuario.
Nao le IQ Option. OHLC tem timestamps UTC, e o analisador recebe apenas barras
ja fechadas. Se o ultimo fechamento estiver velho demais (limite entre 20 e
60 segundos segundo o timeframe), a hipotese da **proxima barra** e AGUARDAR.
Consulta a cada 60/120/300 s conforme plano, nao stream tick-a-tick.
Se houver erro, falta de credito, pausa ou mercado fechado, suspende-se a
analise. Precos da API nao sao necessariamente iguais aos da corretora.

## Ciclo M1 auditavel (motor isolado, ainda sem fonte ao vivo certificada)

`ds_trader/m1_cycle.py` aceita apenas eventos com identidade (ativo, fonte,
M1), relogio confiavel e historico de pelo menos 25 candles consecutivos cujo
fechamento foi **explicitamente comprovado pela fonte**, alem de amostras de
preco etiquetadas `OPEN` e `CLOSE` com horarios de referencia precisos.

- **PENDENTE:** prepara CALL/PUT so antes da abertura-alvo, com antecedencia
  minima de 1 segundo. Se ultimo candle usado fechou em T, alvo = T+60s.
- **ATIVA:** somente se a abertura vier marcada em T+60s, recebida ate 1s
  depois, com preco confirmado. E referencia de teste, nao ordem executada.
- **CONCLUIDA:** somente se o fechamento exato 60s apos a abertura vier
  confirmado (recebido ate 2s depois). Compara precos em ACERTO/ERRO/EMPATE.
- **AGUARDAR:** qualquer atraso maior que as tolerancias, preco invalidado,
  barra aberta, relogio sem fuso, troca de ativo/periodo, lacuna ou ausencia de
  prova. O minuto nao pode ser reutilizado para fabricar outra entrada.

As tolerancias sao parametros tecnicos conservadores, nao permissao de operar
atrasado. A origem precisa comprovar a hora de cada observacao; declarar
`closed_confirmed=True` em dados estimados por pixels seria incorreto. A
API Forex por consultas periodicas nao garante esse nivel de observacao e
**nao esta conectada ao ciclo M1**. Os testes usam amostras artificiais,
nao performance de mercado nem sincronizacao real com a IQ Option.

## Testes e condicoes de liberacao

- Testes unitarios de engolfo, doji, pivos causais, LTA/LTB, recortes falsos,
  draw de linhas e abstencao por dados incompletos.
- Teste GUI no Windows empacotado, atalhos e EXE real, sem autenticar na corretora.
- Validaçao MANUAL de recortes no grafico real, inclusive estabilidade apos troca
  de ativo, timeframe, zoom e janela.
- Backtest em OHLC historico real autorizado, com spread de custos/payout real,
  dados de entrada/saida na hora exata e segmento futuro separado.
- Ate essas etapas, **nao ha estrategia validada** e nenhum sinal deve ser
  apresentado como confiavel ou comprovadamente lucrativo.
