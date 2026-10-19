# Diagnóstico do código recebido e decisões

Inspecionado o repositório Daniel-Soliz/Robo-Das-Binarias no commit `ecfd96306ba9764b1ee56e1417d9628887e25850`.

- Python com dataclass Candle, indicadores, pivôs, zonas, padrões, confluência e testes.
- Entrada antiga exibia logs; PyQt era usado para calibrar captura, não um simulador com histórico e relatórios.
- Captura de tela gerava preços relativos, sem timestamps precisos: não serve à liquidação auditável.
- Adaptador IQ Option importava biblioteca comunitária; tinha reconexão progressiva mas sem limite total, descartava entradas inválidas e removia duplicatas. Não reutilizado para CSV/tempo real.
- Reaproveitados o contrato de OHLC `Candle` e detector estrito `detectar_pivos`, chamado só com janela já fechada. Confluência/score antigos não são usados para a nova estratégia única.
- Código anterior preservado com entrada `legacy_main.py` e documentação LEGADO. Isso permite comparar e reverter; não é incluído como serviço no DS Trader.

## IQ Option — consulta em 19/10/2026

Fontes consultadas:
- https://iqoption.com/en/terms-and-conditions
- https://iqoption.com/pt/terms-and-conditions/terms-conditions?company_id=2
- https://iqoptionapi.github.io/iqoptionapi/

Não foi localizada documentação pública de API oficial, acessível e adequada para esta integração. **Isso não comprova que nenhum acesso contratual exista.** A página de termos é dinâmica e a extração disponível não expôs integralmente os documentos contratuais; não foi possível certificar permissões atuais para extração automatizada. Não se presume autorização.

A documentação da iqoptionapi afirma expressamente que é mantida pela comunidade e não oficial. Ela descreve acesso a candles/conta, mas não demonstra compatibilidade atual nem autorização da corretora. O código legado pede login/senha, não tokens com escopos oficiais verificáveis. Nenhuma credencial foi solicitada, utilizada ou incluída no novo aplicativo.

Não foi confirmada disponibilidade oficial de candles históricos, ticks exatos, payout histórico, preço/regra de liquidação ou calendário de expiração. Portanto a V1 não oferece análise ao vivo nem reprodução fiel da IQ Option. Uma integração posterior depende de documentação/autorização verificável da fonte, autenticação suportada, escopos mínimos de leitura, limites e qualidade dos dados. Reconexão limitada, deduplicação e detecção de atraso deverão ser testadas nessa integração, não simuladas como recurso existente.

CSV local funciona sem conta ou permissões de rede. Usuário fornece dados que tem autorização para utilizar. Ativo, origem e OTC/REGULAR são mantidos separados. CSV sintético é rotulado como SINTETICO-DS-TESTE. Não há substituição por Yahoo/TradingView ou outra fonte.

## Arquitetura local

- `ds_trader/data.py`: importação/validação e hash da entrada.
- `ds_trader/strategy.py`: regras causais; reaproveita Candle/pivôs.
- `ds_trader/simulation.py`: replay, divisão temporal, entrada/liquidação, métricas.
- `ds_trader/storage.py`: SQLite, backup e exportação segura para planilhas.
- `ds_trader/explain.py`: explicações determinísticas; sem serviço externo.
- `ds_trader/ui.py`: interface Tk em português.
- `scripts/build.ps1`: build Windows, teste do executável e pacote portátil.

Sem IA externa na V1: custo zero de API e nenhum dado enviado. Uma extensão futura precisaria tela explícita de provedor, conteúdo enviado e custo, chave em cofre do Windows e falha isolada do motor. Não há esse provedor para habilitar agora.

Configuração e histórico são locais, não criptografados; não armazenam senha. Backup/relatório contém cotações e estudos do usuário. Sem servidor, telemetria ou execução de ordens. O executável inclui Python/Tk; scripts de captura e adaptador não oficial não são importados pelo caminho normal.

## Nova implementação: leitura visual local (integração posterior)

Revisão da separação de responsabilidades: o capturador antigo `data_sources/screen_source.py` depende de OpenCV, OCR/Tesseract e identificação de ativo/timeframe, gerando apenas preços relativos; ele continua no projeto LEGADO e **não é instalado como motor de ordens nem usado para gerar entradas simuladas**.

A nova guia `Tela ao vivo` usa `ds_trader/live_ui.py` (seleção e prévia Tk) e `ds_trader/live_screen.py` (mss + Pillow, processamento em thread). A captura só é iniciada por escolha explícita da área e clique do usuário. A interface recebe frames por fila limitada, sem salvar/transmitir os pixels. O algoritmo busca corpos verde/vermelho e descreve somente variação visual relativa; exclui o candle mais à direita por poder estar aberto. `Assessment.is_market_quote=False` e `Assessment.trading_signal=False` são fixos. Não há obtenção de ticks, pagamento ou horário real a partir da tela.

O modo histórico mantém suas regras, dados verificáveis e armazenamento próprios. Não há mistura automática entre capturas visuais e valores de simulação. O instalador Windows passou a incluir `mss` e `Pillow` em versões fixadas. A interface no Windows, permissões de captura, multi-monitor, DPI e leitura sobre gráficos reais ainda exigem validação manual no equipamento do usuário.
