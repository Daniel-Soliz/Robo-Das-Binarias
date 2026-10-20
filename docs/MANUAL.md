# Manual rápido — DS Trader

**Instalação normal no Windows 10/11 (64 bits):** abra https://daniel-soliz.github.io/Robo-Das-Binarias/, clique em **Baixar instalador** quando disponível, abra `DS-Trader-Setup.exe` e siga o assistente em português. O instalador cria um atalho **DS Trader** na Área de Trabalho e no Menu Iniciar. Clique nele para iniciar. Não precisa instalar Python e não exige administrador. No Windows, use Configurações > Aplicativos para desinstalar.

**Portátil (opcional):** extraia `DS-Trader-Windows-x64.zip` inteiro e abra `DS-Trader/DS-Trader.exe`, sem mover o arquivo para fora da pasta. A instalação antiga por `Instalar.cmd` continua no ZIP, mas o assistente .exe é a forma recomendada. O programa não requer login.

## Como ver pares de Forex com candles recentes

O modo **Forex em tempo real** consulta a API HTTPS da Twelve Data, quando o usuario fornece sua propria chave. Este modo mostra dados de mercado separados da demonstracao sintetica e da aba Tela ao vivo.

1. Se tiver acesso ao fornecedor, gere uma chave em https://twelvedata.com/ . A disponibilidade e o custo dependem do plano.
2. Abra **Forex em tempo real** no DS Trader.
3. Escolha o par (por exemplo EUR/USD) e o intervalo (1min, 5min ou 15min).
4. Selecione a frequencia de atualizacao (120 s recomendado; 60 ou 300 s tambem disponiveis conforme limites da conta).
5. Insira a chave da API **na janela do aplicativo**, nao por mensagens, e clique **Conectar ao mercado**.
6. Confira o selo **ATUALIZADO** ou **ATRASADO**, horario UTC do ultimo candle, tendencia descritiva, medias moveis e suporte/resistencia por pivos.
7. Clique **Desconectar** para interromper a leitura e descartar a chave em memoria.

O aplicativo descarta candles ainda abertos, interrompe a analise de dados sem atualizacao recente e nao cruza lacunas. Nao fornece ticks, entrada nem vencimento da IQ Option e nao envia ordens. Dados Forex do fornecedor podem diferir do preco da corretora. Uma leitura de tendencia NAO e recomendacao para CALL/PUT.

## Proxima vela — novas hipoteses de CALL, PUT ou AGUARDAR

A versao 1.2 do aplicativo exibe a **hipotese da proxima vela**, em vez
de um comando de entrada. Em `Tela ao vivo`, voce vera, quando houver
velas reconhecidas, os padroes e linhas de tendencia LTA/LTB calculadas
visualmente; apenas recortes regulares com pelo menos 26 corpos estimados
sao analisados. **A tela nao confirma o horario de fechamento do candle.**
O sinal visual nao foi validado nem sincronizado a expiracao da IQ Option.

No `Forex em tempo real` a hipotese da proxima barra depende de candles
fechados enviados pela fonte Twelve Data. Dados atrasados geram AGUARDAR.
Esses precos podem ser diferentes dos da IQ Option.

Leia [regras e limites](SINAIS.md). O programa nunca clica para operar,
nao recebe senha da corretora e nao atribui porcentagens ficticias de acerto.

## Monitoramento visual sem fotos enviadas

1. Abra sua plataforma no navegador e mantenha visível o gráfico em candles verdes/vermelhos.
2. No DS Trader entre na guia **Tela ao vivo** e clique **Selecionar área do gráfico**.
3. Arraste para delimitar somente o gráfico. Evite capturar login, saldo, conversas e dados pessoais. Pressione Esc para cancelar.
4. Clique **Iniciar monitoramento**. O aplicativo captura essa região do monitor a cada cerca de 1,2 segundo e exibe a prévia e a observação visual (alta/baixa relativa ou insuficiente).
5. Para interromper, clique em **Parar**. A captura não é automática e não envia imagens à internet.

O leitor depende das cores e do desenho das velas; não é OCR de preços e não confirma horário de fechamento, ativo, payout nem vencimento da IQ Option. A vela mais recente pode estar em formação e não é usada como fechada. Nunca interpretar a observação como sinal CALL/PUT. Se as cores não forem reconhecidas, o sistema deve mostrar leitura insuficiente, não inventar um resultado. Para simulação auditável, importe dados CSV com horários comprovados.

## Simulação com CSV

1. Instale pelo assistente ou abra o portátil, conforme descrito acima.
2. Clique **Exemplo sintético**. O aviso DEMONSTRAÇÃO indica dados inventados para testar o software.
3. Em **Configurações**, veja meia largura, tolerância e prazo de reteste. A largura é preço absoluto: valores iniciais são adequados à escala do exemplo, não a todos os ativos.
4. Clique **Iniciar / continuar**. O gráfico revela barras fechadas em ordem. **Pausar** congela a reprodução; **Avançar uma barra** permite estudar; **Encerrar** finaliza pendências como indeterminadas. Iniciar após encerramento cria nova execução.
5. Em **Sinais e histórico**, clique em um evento para ler a região, critérios e resultado disponível. “Sem sinal” é normal. Não há obrigação de produzir entradas.
6. Em **Resultados**, confira desenvolvimento e teste separadamente. Clique em um histórico salvo para abrir seu relatório. Históricos são preservados ao fechar e reabrir; reprodução em andamento não retoma automaticamente após reabrir.
7. **Exportar relatório** gera um JSON completo e CSVs de eventos e operações na mesma pasta. JSON inclui CSV original: não compartilhe dados que não queira divulgar.
8. Para seus dados: **Importar CSV**, selecionar ativo/origem/mercado/intervalo. Campos De/Até são opcionais: `2025-01-06T09:00:00-03:00`. De limita abertura; Até limita fechamento. Ajuste parâmetros **antes** de iniciar. Nova importação encerra reprodução anterior.
9. **Backup** copia o SQLite. Para restaurar, feche DS Trader, faça uma cópia do banco atual e substitua `%LOCALAPPDATA%\DS Trader\history.sqlite3` pelo backup. Não abra bancos recebidos de desconhecidos.

Payout 0.80 significa lucro de 8 numa aposta simulada de 10. Perda é -10. O app não cresce apostas após perdas. Sem payout histórico, aparece CENÁRIO HIPOTÉTICO. Indeterminadas não são vitórias nem empates, e seu efeito financeiro permanece desconhecido.

CSV com lacunas é rejeitado, inclusive pausas de mercado: importe sessões contínuas separadas. Não preencha candles artificiais para remover erros. Só informe `open_time` quando houver horário observado real da cotação. A origem é a declarada no arquivo; nenhuma cotação é buscada silenciosamente em outro serviço.

A leitura VISUAL da tela está disponível na guia Tela ao vivo, mas não há cotação oficial em tempo real, conexão com a IQ Option ou IA externa. Não existe botão que promete conectar sem integração. Explicações em português funcionam offline, sem custo e sem enviar dados.

Desinstalar a instalação simples: apague atalho e `%LOCALAPPDATA%\Programs\DS-Trader`. Históricos permanecem na pasta separada `DS Trader`; exclua somente se quiser apagar seus estudos.
