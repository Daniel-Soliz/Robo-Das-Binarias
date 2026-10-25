# DS Trader — extensão Chrome (protótipo)

## Estado atual
Este é um protótipo de interface Manifest V3. O botão da extensão injeta um painel flutuante na aba web ativa. O painel ainda **não lê candles da IQ Option**. Foi adicionado um motor técnico experimental separado (`engine.js`), que recebe candles OHLC fechados, valida a estrutura e calcula SMA 9, SMA 21 e RSI 14. Ele retorna uma hipótese técnica experimental, mas não calcula probabilidades nem tem integração com o gráfico ao vivo.

## Testar localmente
1. Baixe esta pasta do repositório ou use o botão **Code → Download ZIP** e extraia o projeto.
2. No Chrome, abra `chrome://extensions`.
3. Ative **Modo do desenvolvedor**.
4. Clique **Carregar sem compactação** e selecione a pasta `extension`.
5. Abra a IQ Option Web, clique no ícone de extensões, escolha DS Trader e clique **Abrir painel**.
6. Para fechar o painel, clique no ×.

## Testes do motor
Com Node.js instalado, execute `node extension/engine.test.js` na raiz do repositório para rodar os testes básicos do motor.

## Próximas etapas
1. Validar visualmente os gráficos e limites dos termos da plataforma.
2. Implementar captura/leitura apenas após confirmar o método compatível, ativo e timeframe.
3. Validar candles fechados, relógio e fonte de dados antes de permitir hipótese CALL/PUT.
4. Calibrar qualquer probabilidade com teste histórico fora da amostra; se os dados falharem, mostrar AGUARDANDO.

A extensão não envia ordens e não acessa credenciais da conta.
