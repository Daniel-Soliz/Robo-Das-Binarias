# Relatório de testes — 19/10/2026

## Executado neste ambiente

`python -m unittest discover -s tests_ds -v`: **23 testes aprovados** (Linux, Python do ambiente; núcleo sem dependências externas).

Cobertura: CSV válido/errado, duplicatas, ordem, lacunas, OHLC, fuso ausente, horários futuros, volume opcional, mercados separados, ausência de cotações; pivôs confirmados, alta/baixa, invalidação/prazo, igualdade de eventos em cada prefixo do histórico (sem uso de futuro), processamento repetido; ganho/perda/empate, payout variável/hipotético, entrada posterior, expiração inexata indeterminada, resultados não revelados antes do vencimento, divisão desenvolvimento/teste, simultaneidade; SQLite reaberto, backup e JSON/CSV; funcionamento com rede indisponível.

`python -m compileall -q ds_trader scripts tests_ds main.py`: sem erros.

## Windows e interface

A máquina local não oferece Windows nem sessão gráfica. **Nenhuma instalação manual Windows 10/11 foi executada localmente.**

Workflow `.github/workflows/testes.yml` prepara Python 3.11.9 x64 em Windows Server 2022, executa a suíte, constrói com PyInstaller e abre o **executável real** com `--smoke-test`. O teste cria janela Tk, desenha candles, avança reprodução, pausa, completa, reabre histórico e exporta. Só produz pacote se o teste passa. Foi adicionado um instalador Inno Setup que instala por usuário, cria atalhos na Área de Trabalho e no Menu Iniciar e contém desinstalador. O script também confere a instalação e a abertura do .exe instalado. A release é publicada automaticamente no GitHub somente após esses testes e verificação SHA-256. Evidência será o status da execução e `smoke-result.json` dentro do artifact. Até a execução concluir, build e GUI permanecem não verificados. Passar no Windows Server não substitui instalação/interação manual em Windows 10/11.

A suíte antiga `tests/` roda separadamente no trabalho `legacy`; não alegamos execução local dela (dependências antigas não instaladas aqui). O build antigo testava instalação simples por script. O novo build usa o instalador Inno Setup; sua execução e publicação ainda precisam ser verificadas no status da execução do GitHub Actions. A desinstalação manual não é testada.

A primeira execução Windows detectou uma leitura de JSON no teste sem encoding explícito. Corrigido para UTF-8; o exportador já gravava em UTF-8. O relatório final deve considerar a execução posterior à correção.

## Limitações que permanecem

- Sem conexão ao vivo, autenticação IQ Option, reconexão de fonte ativa ou IA externa: não aplicáveis os testes de falha desses serviços; apenas independência de rede foi testada.
- Sem dados reais de validação financeira; testes usam somente dados sintéticos. Nenhum índice de rentabilidade é evidência de vantagem de mercado.
- Uma cotação explícita de abertura por barra; sem ticks intrabar, interpolação, ordem real ou liquidação proprietária da corretora.
- Execuções indeterminadas não contam como zero; métricas de saldo representam apenas a parte determinável.
- Parâmetros não são calibrados. Repetir ajustes no teste contamina a avaliação. Wilson pressupõe independência.
- Arquivo completo é rejeitado se há falha; não há calendário de pregão, conversão de formatos livres ou reparo automático.
- Interface mostra últimos 90 candles revelados, sem zoom/arraste; reprodução individual por ativo/fonte/mercado/intervalo. Para comparar ativos, execute cada seleção e exporte seus relatórios.
- Histórico persiste; replay interrompido não retoma o cursor após reiniciar o aplicativo.
- Instalador Inno Setup com assistente gráfico e desinstalador, mas sem assinatura digital; não é MSI. Versão portátil e instalador simples antigo continuam disponíveis.
- Não houve avaliação de desempenho em arquivos grandes. Salvamento local ocorre a cada passo e contém o CSV original.

## Evolução posterior — leitor visual de tela

Foram adicionados `tests_ds/test_live_screen.py` com sete testes unitários para geometria, configuração, imagem em branco e candles coloridos de alta/baixa. Eles verificam também que o modo visual não fornece preço de mercado nem sinal de ordens. O `scripts/gui_smoke.py` agora verifica a existência da aba e a ausência de captura automática.

**Status:** as alterações foram gravadas no GitHub, mas NÃO há evidência confirmada neste relatório de que o novo CI Windows tenha ficado verde ou que o instalador atualizado tenha sido publicado. A captura real de tela no Windows, com diferentes plataformas, resoluções e tema de cores, NÃO foi validada. Nenhuma alegação de acerto financeiro pode ser baseada no modo visual.

A fila de frames tem capacidade 1, descartando imagens antigas para reduzir atraso; a captura é executada em thread dedicada. Erros interrompem a captura com mensagem em tela. Não são enviados pixels ou credenciais para servidores por este modo. A leitura é aproximada, pode falhar em temas distintos, sobreposições, várias janelas, monitores e DPI.
