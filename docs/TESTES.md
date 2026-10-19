# Relatório de testes — 19/10/2026

## Executado neste ambiente

`python -m unittest discover -s tests_ds -v`: **23 testes aprovados** (Linux, Python do ambiente; núcleo sem dependências externas).

Cobertura: CSV válido/errado, duplicatas, ordem, lacunas, OHLC, fuso ausente, horários futuros, volume opcional, mercados separados, ausência de cotações; pivôs confirmados, alta/baixa, invalidação/prazo, igualdade de eventos em cada prefixo do histórico (sem uso de futuro), processamento repetido; ganho/perda/empate, payout variável/hipotético, entrada posterior, expiração inexata indeterminada, resultados não revelados antes do vencimento, divisão desenvolvimento/teste, simultaneidade; SQLite reaberto, backup e JSON/CSV; funcionamento com rede indisponível.

`python -m compileall -q ds_trader scripts tests_ds main.py`: sem erros.

## Windows e interface

A máquina local não oferece Windows nem sessão gráfica. **Nenhuma instalação manual Windows 10/11 foi executada localmente.**

Workflow `.github/workflows/testes.yml` prepara Python 3.11.9 x64 em Windows Server 2022, executa a suíte, constrói com PyInstaller e abre o **executável real** com `--smoke-test`. O teste cria janela Tk, desenha candles, avança reprodução, pausa, completa, reabre histórico e exporta. Só produz pacote se o teste passa. Evidência será o status da execução e `smoke-result.json` dentro do artifact. Até a execução concluir, build e GUI permanecem não verificados. Passar no Windows Server não substitui instalação/interação manual em Windows 10/11.

A suíte antiga `tests/` roda separadamente no trabalho `legacy`; não alegamos execução local dela (dependências antigas não instaladas aqui). O script de instalação por usuário não tem teste automático de atalho/desinstalação nesta revisão.

## Limitações que permanecem

- Sem conexão ao vivo, autenticação IQ Option, reconexão de fonte ativa ou IA externa: não aplicáveis os testes de falha desses serviços; apenas independência de rede foi testada.
- Sem dados reais de validação financeira; testes usam somente dados sintéticos. Nenhum índice de rentabilidade é evidência de vantagem de mercado.
- Uma cotação explícita de abertura por barra; sem ticks intrabar, interpolação, ordem real ou liquidação proprietária da corretora.
- Execuções indeterminadas não contam como zero; métricas de saldo representam apenas a parte determinável.
- Parâmetros não são calibrados. Repetir ajustes no teste contamina a avaliação. Wilson pressupõe independência.
- Arquivo completo é rejeitado se há falha; não há calendário de pregão, conversão de formatos livres ou reparo automático.
- Interface mostra últimos 90 candles revelados, sem zoom/arraste; reprodução individual por ativo/fonte/mercado/intervalo. Para comparar ativos, execute cada seleção e exporte seus relatórios.
- Histórico persiste; replay interrompido não retoma o cursor após reiniciar o aplicativo.
- Pacote sem assinatura, instalação simples por script, sem MSI/assistente gráfico.
- Não houve avaliação de desempenho em arquivos grandes. Salvamento local ocorre a cada passo e contém o CSV original.
