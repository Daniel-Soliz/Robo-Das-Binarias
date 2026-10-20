# Interface DS Trader 1.3 — painel moderno

## Alterações

O aplicativo abre diretamente na guia Tela ao vivo. Essa guia foi redesenhada no módulo ds_trader/live_modern_ui.py.
O gráfico capturado aparece à esquerda; à direita ficam CALL, PUT ou AGUARDAR,
padrões, estruturas LTA/LTB e explicação. O tema escuro foi aplicado ao
desktop pelo módulo ds_trader/theme.py usando o Tkinter/ttk nativo.
A simulação histórica, Forex por API e banco SQLite foram preservados.

## Uso

1. Deixe o gráfico da IQ Option visível no navegador. Posicione janelas
   lado a lado ou use dois monitores, sem que o DS Trader oculte o gráfico.
2. Clique em Selecionar gráfico. O DS Trader se oculta temporariamente para
   facilitar a seleção. Arraste sobre SOMENTE os candles, sem menus, saldo,
   botões CALL/PUT ou barra do navegador. Esc cancela a seleção.
3. De volta ao DS Trader, clique em Iniciar análise. A prévia e a lateral
   serão atualizadas aproximadamente a cada 1,2 segundo.
4. Se a janela do DS Trader estiver sobrepondo mais de uma pequena parte da
   região selecionada, o painel mostrará AGUARDAR — GRÁFICO ENCOBERTO.
   Mova/redimensione as janelas; o programa não pode ver através delas.
5. Clique em Parar para interromper a captura. Nenhuma imagem é enviada.

O período M1/M5/M15 no painel é uma informação inserida manualmente,
NÃO um reconhecimento automático do candle da IQ Option. A captura
visual não confirma o instante exato do fechamento ou expiração.

## Limites

CALL/PUT são hipóteses visuais experimentais, não sinais validados.
O sistema não envia ordens e não calcula probabilidade real de acerto.
Recortes ruins, velas mescladas, janelas encobertas e falta de confluência
levam a AGUARDAR. O monitor não substitui cotações oficiais com timestamps.

## Testes de aceitação

- Rodar: python -m unittest discover -s tests_ds -v
- Rodar smoke test de interface no Windows (scripts/gui_smoke.py), exigindo
  tema, painel, seleção e estado AGUARDAR ao interromper.
- Compilar e testar instalador do Windows com scripts/build.ps1 e Inno Setup.
- Fazer validação manual em Windows 10/11, com navegador e DS Trader lado
  a lado, trocar zoom/período, selecionar outro gráfico, testar Esc e Parar.
- Não alegar executável pronto sem confirmação de CI verde e publicação.

A atualização foi projetada para instalar por cima da anterior, com o
programa fechado e mantendo dados locais de histórico.
