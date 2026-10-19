# Manual rápido — DS Trader

**Instalação normal no Windows 10/11 (64 bits):** abra https://daniel-soliz.github.io/Robo-Das-Binarias/, clique em **Baixar instalador** quando disponível, abra `DS-Trader-Setup.exe` e siga o assistente em português. O instalador cria um atalho **DS Trader** na Área de Trabalho e no Menu Iniciar. Clique nele para iniciar. Não precisa instalar Python e não exige administrador. No Windows, use Configurações > Aplicativos para desinstalar.

**Portátil (opcional):** extraia `DS-Trader-Windows-x64.zip` inteiro e abra `DS-Trader/DS-Trader.exe`, sem mover o arquivo para fora da pasta. A instalação antiga por `Instalar.cmd` continua no ZIP, mas o assistente .exe é a forma recomendada. O programa não requer login.

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

Modo ao vivo e IA externa não estão disponíveis. Não existe botão que promete conectar sem integração. Explicações em português funcionam offline, sem custo e sem enviar dados.

Desinstalar a instalação simples: apague atalho e `%LOCALAPPDATA%\Programs\DS-Trader`. Históricos permanecem na pasta separada `DS Trader`; exclua somente se quiser apagar seus estudos.
