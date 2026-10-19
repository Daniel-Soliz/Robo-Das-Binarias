# Regras definidas para v1.0.0

Todos os valores iniciais são **hipóteses de teste**, sem validação financeira.

| Parâmetro | Inicial | Regra |
|---|---:|---|
| left / right | 2 / 2 | Topo estritamente maior que máximas vizinhas; fundo estritamente menor que mínimas. Empates não formam pivô. Confirmado só no fechamento do segundo candle à direita. |
| min_touches | 2 | Dois pivôs do mesmo tipo dentro da região. |
| separation | 3 | Distância mínima entre índices de pivôs aceitos como toques. |
| width | 0.0002 | Meia largura absoluta em unidades de preço. Região = primeiro pivô ± largura; centro não muda. Ajustar à escala do ativo. |
| breakout | 0.00005 | Distância além da borda para confirmação por fechamento. |
| retest_bars | 5 | Até cinco candles após o rompimento para retestar e confirmar. |
| zone_age | 200 | Idade máxima desde o último toque para aceitar rompimento ou novo toque na região. |

Os pivôs são processados cronologicamente. Se couber em várias regiões, o novo toque pertence à primeira região compatível criada. Região confirmada no fechamento atual só pode ser rompida a partir do próximo candle. Regiões consumidas não recebem novos toques. Isso evita mudar retroativamente a região usada pelo padrão.

**Alta:** fechamento anterior <= borda superior + tolerância; fechamento atual > esse limite. Congela região e aguarda outro candle. O reteste exige interseção da amplitude com a região, fechamento > borda superior + tolerância e fechamento > abertura. Sinal fica disponível no fechamento desse candle, nunca no seu início.

**Baixa:** condições espelhadas: cruza para baixo da borda inferior - tolerância; candle posterior toca a região, fecha abaixo desse limite e abaixo da abertura.

**Invalidação:** fechamento além da borda oposta acrescida da tolerância, ou mais de N candles após o rompimento sem confirmação. Encerramento/divisão do estudo também encerra padrões pendentes e registra motivo. A invalidação tem precedência sobre a confirmação. Um pavio além da região, isoladamente, não invalida.

Uma região é consumida no primeiro rompimento, mesmo se o reteste falhar. Novos pivôs podem criar outra região depois. Há somente um padrão em espera por série. Se várias regiões rompem juntas, prevalece a primeira criada elegível. Só há uma operação/entrada pendente por reprodução; novos sinais nesse intervalo ficam registrados como IGNORADO. Não há cooldown probabilístico ou martingale.

# Entrada e liquidação

| Parâmetro | Inicial | Significado |
|---|---:|---|
| duration | 120 s | Duração desde a entrada, independente do intervalo de candle |
| delay | 1 s | Atraso mínimo após disponibilidade do sinal |
| max_wait | 60 s | Espera adicional máxima após atraso |
| stake | 10 | Valor fixo em unidades monetárias |
| payout | 0.8 | Lucro por unidade apostada, apenas se CSV não fornecer payout na entrada |
| tie | refund | Igualdade de preço devolve valor; loss faz empate perder stake |
| development | 0.7 | Primeiros 70% das barras para desenvolvimento, restante teste |

Primeira cotação `open` com `open_time` estritamente após sinal, e >= sinal + atraso, até sinal + atraso + espera. Não usamos o fechamento do sinal para executar. Uma cotação com horário exatamente igual ao sinal nunca é entrada. Liquidação somente se houver cotação com horário **igual** a entrada + duração. Falta de precisão => indeterminada; lucro nulo no campo JSON (`null`), nunca zero artificial.

Candle fechado não dá timestamps de cada negociação. O usuário precisa preservar o timestamp real de `open` em `open_time`; esse campo é uma declaração da fonte, não prova produzida pelo programa. O modelo não reproduz slippage, rejeições, latência de corretora, preço proprietário de liquidação ou calendário de expiração da IQ Option. Portanto resultado determinável é do **modelo local**, não uma operação que a corretora necessariamente liquidaria igual.

Desenvolvimento e teste têm motores separados. No corte, operações ainda abertas viram indeterminadas, padrões são encerrados e zonas reiniciadas. Parâmetros ficam congelados durante a reprodução e aparecem no relatório. Não há otimização: usar repetidamente o teste para escolher parâmetros contamina a avaliação. O usuário deve reservar novos dados não vistos para uma avaliação posterior.

Saldo inicia em zero como P&L acumulado; valor de entrada é fixo e não há bloqueio por saldo insuficiente. Drawdown e lucro consideram somente liquidações determináveis. Indeterminadas interrompem a sequência observada de perdas; não presumimos seu resultado. Wilson 95% usa acertos/(acertos+erros), excluindo empates e indeterminadas. Não mede confiança em um sinal. Equilíbrio 1/(1+p) vale para acerto +p e erro -1; empate-perda exige considerar seu impacto adicional. Payout variável é aplicado em cada operação, sem taxa única de equilíbrio.
