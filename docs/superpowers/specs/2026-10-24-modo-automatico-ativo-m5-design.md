# DS Trader — Modo Automático por Ativo (M5)

## Intenção e aprovação

Daniel confirmou em 24/10/2026: **M5 é o período principal** e autorizou
implementar por etapas, preservando dados. Ao mudar de par na IQ Option, o
aplicativo deve identificar o **par da janela**, buscar um histórico público
correspondente de até 24h e explicar o cenário técnico de CALL/PUT/AGUARDAR.
Nunca executar ordens financeiras reais.

## Abordagens

1. **Somente pixels:** nenhuma API, mas não comprova candles fechados anteriores
   ou histórico não visível. Insuficiente para 24h e horário da próxima vela.
2. **Somente mercado externo:** histórico confiável, mas perde o par ativo e
   pode confundir mercado Spot/Forex com cotações específicas da IQ Option.
3. **Híbrida escolhida:** leitura local do cabeçalho e identidade estável +
   histórico verificado de fonte pública, com apresentação separada, rótulo
   inequívoco e bloqueio operacional quando a equivalência não é comprovada.

## Regras de produto

- Reconhecimento exige `AssetIdentity` confirmada pelo guardião atual em três
  frames do mesmo fluxo e ignora leituras antigas, ambíguas ou perdidas.
- Confirmação de par é literal; não inverter `USD/NZD` em `NZD/USD`, não
  reinterpretar USD como USDT, não fingir disponibilidade de Forex OTC.
- Troca de par, período, flag OTC ou perda de OCR invalida imediatamente toda
  análise anterior; pedidos HTTP anteriores nunca reaparecem na UI.
- O alvo **M5** usa até 288 candles fechados consecutivos para estudar 24h;
  com menos dados informa o horizonte efetivo e pode marcar `AGUARDAR`.
- Binance Spot `/USDT` e Kraken Spot `/USD` funcionam sem login quando
  disponíveis; Forex requer fonte Twelve Data com chave informada somente em
  memória na sessão. Sem chave ou sem par coberto, `SEM FONTE`, não um preço.
- O motor de histórico produz **cenário descritivo** de alta/baixa/neutro com
  confluências entre SMA 9/21, formação de candles, suportes/resistências,
  pivôs e estrutura. Sem percentuais fictícios ou promessa de eficácia.
- Nunca mostrar `CALL` ou `PUT` **como entrada verificada na IQ Option** apenas
  com dados de outra fonte. O aviso de cenário externo é visível; o estado de
  decisão operacional permanece **AGUARDAR** até confirmação de fonte e
  sincronização com a corretora, que ainda não existe neste projeto.
- Candle aberto, série com lacunas, dado vencido, tempo invertido, sessão Forex
  fechada, falta de fonte e OTC bloqueiam o alerta de próxima vela. Não enviar
  ordens, não iniciar conexão privada com IQ Option.
- HTTP nunca bloqueia Tk; consultas têm timeout, geração de identidade e fila
  limitada. Segredos não vão para log, relatório, arquivo ou banco SQLite.
- Preservar arquivos do usuário, banco local, configurações, menus e fluxos
  existentes. Janela Windows/GUI e OCR real precisam de validação no Windows.

## Fases

1. Motor testável para avaliação M5 a partir de candles públicos já fechados,
   com comparação de 24h, verificação de horizonte/continuidade e explicação.
2. Adaptadores para histórico ampliado e consulta correspondente ao par ativo
   sem login para cripto e com chave opcional para Forex.
3. Controlador isolado de foco ativo com cancelamento por geração, resultado
   separado na interface e testes de troca de par/OTC/atraso/falha de fonte.
4. Verificação automatizada e teste do ambiente Windows quando disponível.

## Limitações explícitas

- Os widgets TradingView não são uma API extraível de candles.
- Disponibilidade, créditos e eventual atraso do Twelve Data dependem do
  fornecedor/plano; atraso intradiário pode tornar M5 impróprio para entrada
  na abertura da próxima vela.
- A análise será de **referência externa**, não sinal de operação na IQ Option.
