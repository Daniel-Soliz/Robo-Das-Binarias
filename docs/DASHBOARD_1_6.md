# DS Trader 1.6 — dashboard redesenhado

## Referência de interface

Remodelação baseada na captura aprovada do DS Trader com navegação
vertical, cabeçalho de ações, gráfico à esquerda, painéis de análise à
direita e barra de status na parte inferior.

Implementações separadas por responsabilidade:
- \`ds_trader/dashboard_shell.py\`: cabeçalho, botões de ação, sidebar,
  visão de navegação e rodapé de estado. Não acessa cotações.
- \`ds_trader/forex_dashboard.py\`: apresentação do Forex em painéis
  usando por herança \`forex_ui.ForexMarketTab\` para **preservar** o
  worker da API, a chave temporária e a lógica de conexão/desconexão.
- \`ds_trader/ui.py\`: integra navegação lateral ao ttk.Notebook existente,
  oculta abas antigas no topo, exibe a nova visão geral e conserva
  referências públicas usadas nos testes e no simulador.
- \`ds_trader/theme.py\`: novo estilo de notebook sem cabeçalhos visíveis.

## Estrutura e comportamento

### Barra lateral
Visão geral, Gráfico e reprodução, Forex em tempo real, Tela ao vivo,
Sinais e histórico, Resultados, Configurações e Ajuda. Os botões
selecionam páginas reais, não são apenas imagens ou placeholders.

### Cabeçalho
Importar CSV, Exemplo sintético, Exportar relatório e Backup permanecem
ligados às funções originais; não alteram automaticamente o Forex.

### Forex
Área superior com par, período (1/5/15 min), atualização, chave API
mascarada e botões funcionais Conectar/Desconectar.

A área de gráfico à esquerda desenha candles reais recebidos do
fornecedor ou uma linha de fechamento quando esse modo é escolhido.
O botão de expansão oculta/reexibe os painéis laterais. Quando não
há conexão, **nenhum candle real é desenhado**: a grade e os símbolos
escuros são decoração identificada pelo aviso "Aguardando conexão".

Na direita, os cartões de tendência, LTA/LTB e suporte/resistência só
mostram informações após existir \`MarketView\` atualizado. Sem dados
ou com feed atrasado, o cartão principal exibe AGUARDAR.

### Tela ao vivo
A guia de captura local permanece integrada ao menu lateral. Seus
candles detectados via pixels e as hipóteses de padrões continuam
experimentais. O sistema não confirma preço/tempo da IQ Option e
o ciclo M1 verificável exige relógio e fonte de quote apropriados.

## Testes

\`scripts/gui_smoke.py\` confere:
- navegação lateral com oito entradas e página Forex selecionada;
- mudança efetiva entre visão geral, Tela ao vivo e Forex;
- feed Forex desconectado e painel AGUARDAR antes da chave;
- manutenção dos testes históricos, exportação e persistência;
- nenhuma captura ou ordem automática.

\`python -m unittest discover -s tests_ds -v\` continua sendo a
suíte do núcleo, e o workflow GitHub Actions compila, instala e
testa o EXE no Windows antes de publicar a release.

**Atenção:** o efeito visual pode variar ligeiramente conforme
resolução e escalonamento DPI do Windows. Não alegar validação
visual completa sem abrir a versão instalada num PC real.
