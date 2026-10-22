# Interface DS Trader 1.4 — painel moderno e janela fixada

## Alterações

O aplicativo abre diretamente na guia Tela ao vivo. Essa guia foi redesenhada no módulo ds_trader/live_modern_ui.py.
O gráfico capturado aparece à esquerda; à direita ficam CALL, PUT ou AGUARDAR,
padrões, estruturas LTA/LTB e explicação. O tema escuro foi aplicado ao
desktop pelo módulo ds_trader/theme.py usando o Tkinter/ttk nativo.
A simulação histórica, Forex por API e banco SQLite foram preservados.

## Uso

1. Deixe a janela do gráfico visível no navegador durante a **seleção inicial**.
2. Clique em Fixar janela do gráfico. O DS Trader se oculta temporariamente para
   facilitar a seleção. Arraste dentro da janela-alvo SOMENTE sobre os candles, sem menus, saldo,
   botões CALL/PUT ou barra do navegador. Esc cancela a seleção.
3. De volta ao DS Trader, confirme o titulo abreviado da janela fixada e clique
   em Iniciar análise. A prévia e a lateral atualizam com quadros recebidos
   daquela janela, mesmo se outro aplicativo estiver por cima.
4. Nao minimize nem feche a janela capturada. Se o aplicativo parar de desenhar
   quadros, o DS Trader informa e interrompe em vez de exibir imagem velha
   como se estivesse ao vivo. Ao redimensionar, reconfigure a area se necessario.
5. Clique em Parar para interromper a captura. Nenhuma imagem é enviada.

O período M1/M5/M15 no painel é uma informação inserida manualmente,
NÃO um reconhecimento automático do candle da IQ Option. A captura
visual não confirma o instante exato do fechamento ou expiração.

A fixacao usa Windows Graphics Capture e depende de suporte do Windows/GPU;
a disponibilidade e verificada ao iniciar. Nao existe garantia de capturar
conteudo protegido ou de receber quadros de uma janela minimizada.

## Limites

CALL/PUT nao sao liberados na captura visual, pois esta nao prova o horario
do fechamento. A tela continua exibindo padroes e linhas tecnicas, com
**AGUARDAR** no painel de proxima vela.
O sistema não envia ordens e não calcula probabilidade real de acerto.
Recortes ruins, velas mescladas, janelas encobertas e falta de confluência
levam a AGUARDAR. O monitor não substitui cotações oficiais com timestamps.

## Testes de aceitação

- Rodar: python -m unittest discover -s tests_ds -v
- Rodar smoke test de interface no Windows (scripts/gui_smoke.py), exigindo
  tema, painel, seleção e estado AGUARDAR ao interromper.
- Compilar e testar instalador do Windows com scripts/build.ps1 e Inno Setup.
- Fazer validação manual em Windows 10/11: selecionar navegador, cobri-lo com
  outra janela, verificar que a previa continua no alvo, mover a janela,
  minimizar/restaurar, fechar, trocar zoom/período e testar Esc e Parar.
- Não alegar executável pronto sem confirmação de CI verde e publicação.

A atualização foi projetada para instalar por cima da anterior, com o
programa fechado e mantendo dados locais de histórico.
