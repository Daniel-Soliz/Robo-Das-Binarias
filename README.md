# DS Trader — Monitor visual e radar de mercado

## Instalação pelo site Robo das Binárias

O visitante usa o botão **Baixar instalador** da página
`https://daniel-soliz.github.io/Robo-Das-Binarias/`. A página procura
`DS-Trader-Setup.exe` na última versão publicada em GitHub Releases e só
habilita o botão quando o arquivo existe. O ZIP é apenas um formato de
transporte do código entre desenvolvedores, não o download do usuário final.

Esta revisão prepara o instalador Windows para levar Python, bibliotecas e
Tesseract OCR com o modelo inglês dentro do pacote, criando atalho e
desinstalador. O build bloqueia a entrega se o OCR estiver ausente. Ainda é
necessário **compilar e verificar o EXE em Windows** antes de publicar a
versão. O aplicativo abre no **Radar M5** e consulta criptomoedas públicas
quando houver rede; Forex exige chave Twelve Data válida e a leitura da IQ
Option depende da janela visível e da confirmação do cabeçalho. Sem fonte ou
sincronização confirmada, o estado é `AGUARDAR`.

Aplicativo desktop em português para leitura visual consentida de gráficos, radar por fonte externa e estudos históricos de **rompimento e reteste**. Importa CSV, reproduz cronologicamente, explica eventos, simula e exporta resultados. **Não envia ordens nem conecta à conta da corretora.**

## Arquitetura híbrida — mercados públicos (código em validação)

### Novo: seguir automaticamente o ativo visível (M5, até 24 horas)

O Monitor agora inicia em **M5**. Quando uma janela IQ Option é fixada e o
OCR local confirma o mesmo símbolo/período após três leituras, a faixa
**ATIVO DETECTADO · HISTÓRICO M5 ATÉ 24 HORAS** passa a consultar, em uma
thread separada, a fonte de mercado exata para aquele par. Trocar `USD/JPY`
por `USD/BRL` invalida imediatamente o resultado antigo, inclusive se uma
resposta HTTP atrasada chegar depois da troca. Falha de OCR, frame atrasado,
outro período ou ativo OTC também invalida o cenário. Um par inverso
(`USD/NZD` e `NZD/USD`) nunca é substituído silenciosamente.

- **Cripto Binance `/USDT` e Kraken `/USD`:** histórico M5 público ampliado
  para até 288 candles realmente fechados. A consulta real Binance de teste
  retornou 288 candles M5 / 24h, sem chave.
- **Forex (`USD/JPY`, `USD/NZD`, `USD/BRL` etc.):** o identificador funciona
  para pares válidos, mas o histórico M5 requer uma fonte autorizada. A
  chave Twelve Data é opcional e digitada no Radar, somente em memória. A
  disponibilidade do par, créditos, feriados e eventuais atrasos são do
  fornecedor. Sem chave aparece `SEM FONTE`, sem inventar candles.
- **Análise:** exige pelo menos 12 horas contínuas, aceita no máximo 24
  horas fechadas, verifica OHLC, ordem, duração, horário e atualização.
  Reaproveita regras explicáveis para tendência SMA 9/21, pivôs, padrões e
  confluências. O resultado tem sempre motivo e fonte identificada.
- **Segurança:** `CALL` e `PUT` podem aparecer apenas como **cenário de
  referência externa**, nunca como entrada validada na IQ Option. O estado
  operacional continua `AGUARDAR` enquanto não houver preços e horários
  comprovadamente sincronizados com a corretora. Após 120s sem novo candle
  fechado a hipótese exibida expira, mesmo antes da próxima consulta HTTP.

O reconhecimento da janela por título e o OCR do cabeçalho são coisas
diferentes: o build Windows atualizado **inclui o executável Tesseract OCR e
seus dados ingleses**; em desenvolvimento, ainda é possível usar o Tesseract
do `PATH`. Sem o motor OCR funcional não há identidade confirmada, e o sistema
mantém `AGUARDAR`. A integração gráfica, OCR embutido, desempenho e
detecção sobre layouts reais da IQ Option precisam de teste em Windows.
Não existe modelo de IA treinado, taxa de acerto medida ou integração com
ordens da corretora nesta etapa.

O aplicativo agora contém **Monitor / Radar / Histórico** na navegação principal
e abre inicialmente no Radar M5.
`Ferramentas` mantém o Forex anterior, simulador CSV, resultados, configurações,
visão geral e ajuda. No Monitor, a parte inferior resume seis favoritos
iniciais (`BTC/USDT`, `ETH/USDT`, `BTC/USD`, `ETH/USD`, `EUR/USD`, `GBP/USD`); abra **Radar** para editar
até 25 favoritos Forex e cripto. Nenhuma linha mostra valores inventados
enquanto não houver conexão.

### Radar sem cadastro para cripto; Forex opcional com chave

1. Abra o DS Trader. O radar inicializa **dois provedores públicos de cripto**,
   **sem criar conta ou chave**: Binance Spot `BTC/USDT`, `ETH/USDT` via
   WebSocket (com histórico REST inicial), e Kraken Spot `BTC/USD`, `ETH/USD`
   via consultas periódicas. Cada símbolo tem sua própria fonte e moeda de
   cotação; USDT **não é USD**. Esses preços não pertencem à IQ Option e não
   equivalem a ativos OTC. A consulta pode demorar e sofrer interrupções.
2. Forex intradiario (`EUR/USD`, `GBP/USD` etc.) continua **sem fonte** ate
   configurar uma chave pessoal Twelve Data no proprio aplicativo. Confira a
   cobertura e o limite de creditos do seu plano; nao envie a chave por chat.
   Ela nao e salva no banco nem nos relatorios.
3. Abra **Radar** para alterar ate 25 favoritos e o periodo M1/M5/M15,
   sendo no máximo dez pares Binance `/USDT` num WebSocket combinado. O
   programa só analisa candles Binance com evento `x=true` e horário de
   fechamento válido. Demais pares continuam na consulta programada Kraken /
   Twelve Data; sem chave o Kraken respeita 2 s entre consultas e 120 s por
   ativo. Na falha do WebSocket a linha é marcada como erro e a conexão tenta
   recuperar com pausas progressivas. Nunca envia ordens.
4. A tela mostra apenas os símbolos realmente recebidos, datas UTC de
   fechamento, situação atual/atrasada/indisponível, média e tendência
   descritivas. Dados envelhecidos deixam de mostrar direção.
5. Clique em **Ver B3, Forex e Cripto no TradingView**. O painel oficial abre
   no navegador padrão, com abas Brasil/Forex/Cripto. **As cotações gratuitas
   da B3 têm atraso aproximado de 15 minutos.** Esse widget apenas mostra
   referências visuais: ele não fornece candles nem sinais ao Radar.
6. Para encerrar a análise, use **Parar**. Uma chave informada e limpa do campo.

Isso **não é streaming tick a tick nem monitoramento irrestrito** de todos
os mercados. O WebSocket Binance emite snapshots de candles Spot fechados;
o TradingView só apresenta uma seleção de símbolos, sem análise automatizada
da B3. Dados B3 realmente ao vivo para cálculo intradiário exigem
licenciamento/fonte autorizada. Os preços de Binance/Kraken/Twelve Data podem
diferir da IQ Option, sobretudo OTC. O aplicativo nunca trata duas origens
como equivalentes.

### Deteccao automatica da IQ Option no Windows

Com **Detectar IQ Option** ligado (padrao Windows), o monitor procura a
cada ~1,5s uma unica janela cujo titulo comece com "IQ Option". Apos duas
observacoes iguais, seleciona um **recorte central estimado** e tenta
iniciar a captura sem cliques. Se voce mudar o layout ou nao enxergar as
velas, selecione manualmente a regiao correta. Janelas pequenas, fechadas,
minimizadas, ambiguas ou com titulos nao reconhecidos nao sao anexadas.
**Parar** desativa a redeteccao ate reativar a caixa de selecao.

Reconhecer a janela nao comprova qual par, periodo ou vencimento estao
visiveis. Se a leitura falhar, o estado permanece `AGUARDAR`. O desempenho
do OCR, a captura WGC e o recorte automatico dependem de validacao no
Windows real; o recurso nao le dados privados da conta IQ Option.

### Troca do ativo visível na IQ Option

O monitor agora tem um guardião de identidade separado da leitura geométrica:
uma identidade precisa permanecer igual em três observações de cabeçalho
para ser mostrada como confirmada. Quando a observação muda ou fica ilegível,
o estado anterior é invalidado imediatamente; durante a transição mostra
`AGUARDAR`. Um OCR local lê uma faixa acima da região marcada
para tentar identificar ativo, período e OTC. Sem OCR funcional, ou se a
interface da IQ Option mudar, a identidade
permanece **não confirmada**; a captura visual pode continuar exibindo o
gráfico, mas não anuncia o novo ativo como reconhecido. O OCR e os recortes
necessitam de validação manual em Windows real.
Por segurança, **cada quadro é associado à sua própria leitura de
cabeçalho**. Um quadro sem leitura não herda o ativo antigo. Quadros fora de
ordem ou com mais de 2,5 segundos de idade não são apresentados como análise
atual, incluindo o tempo de espera da fila até o Tkinter.

Esta é uma **etapa de código e testes automatizados**, com verificação pontual
das fontes públicas Binance e Kraken, mas ainda sem captura real da IQ Option,
teste visual Windows nem compilação do instalador desta versão. A implementação
não contém modelo de IA treinado e não estima
probabilidades verificadas de acerto.

## Interface desktop renovada (v1.9)

### Painel principal renovado

A interface atual prioriza uma barra superior com **Monitor / Radar /
Histórico**, retirando a barra lateral permanente para dar mais espaço ao
gráfico. Na tela Monitor, o cenário da próxima vela aparece em destaque,
separado do estado de validação **AGUARDAR**. Uma faixa abaixo da imagem
mostra o tempo real de processamento e a idade do quadro recebido, quando
medidos na própria máquina. A atualização solicitada é de 550 ms e a
reprodução da prévia não acumula quadros antigos; são limites desejados,
não promessas de latência no Windows ou na corretora.

O aplicativo abre diretamente em **Monitor**. A navegação principal tem apenas
**Monitor**, **Radar** e **Histórico**; simulador, Forex antigo, relatórios,
configurações, ajuda e visão geral continuam no menu **Ferramentas**. Importação de CSV,
exemplo sintético, exportação e backup ficam em **Arquivos**.

No monitor, o procedimento é **1 · Selecionar gráfico → 2 · Iniciar análise**.
O gráfico, o estado **AGUARDAR** e os padrões/estruturas aparecem juntos.
O gráfico também mostra linhas de **SUPORTE VISUAL** e **RESIST. VISUAL**
quando existem pivôs reconhecíveis, além de LTA/LTB. O painel resume o viés
visual (alta/baixa) sem exibir porcentagens de acerto inventadas. As linhas
são estimativas em coordenadas da imagem, **não preços negociáveis**.
Quando não há pivô suficiente, a prévia distingue **TOPO RECENTE** ou
**FUNDO RECENTE** de uma resistência/suporte confirmados. O cartão
**PRÓXIMA VELA · CENÁRIO VISUAL** compara tendências, LTA/LTB e impulso;
mostra ALTA FAVORECIDA, BAIXA FAVORECIDA ou SEM VANTAGEM CLARA com motivos.
Estar perto de um topo/fundo oposto bloqueia uma conclusão apressada.
O estado operacional permanece **AGUARDAR** se fechamento/relógio não forem
verificáveis por captura visual, mesmo com um cenário favorecido.
O cenário atual é calculado por visão computacional e regras explicáveis;
**não há um modelo de IA treinado ou probabilidade calibrada de alta/baixa**.
Para isso seria necessário um histórico confiável da mesma fonte, rótulos
temporais e avaliação fora da amostra, separados do motor visual.

### Velocidade e verificação

- O monitor captura quadros em segundo plano e mantém apenas o mais novo.
- O painel exibe **PROCESSAMENTO** (tempo gasto pelo motor) e **IDADE DO QUADRO**
  (tempo transcorrido desde a captura até a entrega da análise).
- Pode-se medir um print sem rede com `python scripts/benchmark_visual.py print.jpg
  --crop 100 90 1300 635 --runs 100`, ajustando o recorte às velas.
- O pipeline Windows de CI realiza smoke test com interface gráfica real,
  instalação e abertura do executável antes de publicar a release. Testes
  locais em ambiente sem tela não substituem esse teste.
O detector ignora linhas horizontais extensas que algumas plataformas desenham
em vermelho/verde, reduzindo falhas de reconhecimento de candles.
O detalhamento do ciclo M1 e a explicação extensa ficam em **Detalhes técnicos**,
fechados inicialmente. A prévia é atualizada em ritmo reduzido para evitar
repinturas desnecessárias no Tkinter; os estados textuais continuam consumindo
todos os resultados recebidos da análise em segundo plano. A captura pode
ficar atrasada ou ser incapaz de reconhecer candles: nenhum valor de acerto,
preço, horário de entrada ou vencimento é inventado.

### Habilidades externas do vídeo `day-trader-skill` (opcional)

O repositório [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
contém **11 habilidades para Claude Code**, voltadas principalmente a ações
dos EUA, dados públicos e simulações. Não é um leitor da IQ Option e não
transforma pixels em cotações verificadas. Para instalar **as 11 habilidades
no Claude Code deste projeto**, execute na raiz do repositório, com Git e
Claude Code já instalados:

```powershell
powershell -NoProfile -File .\scripts\install-day-trader-skill.ps1
```

O instalador baixa apenas a revisão fixada (`3d0f4ef`), confere a estrutura
e copia para `.claude/skills/` sem substituir pastas existentes. Não executa
as habilidades, não envia ordens e **não faz parte do instalador Windows do
DS Trader**. Os módulos de corretora e carteira da habilidade são para
outro mercado; devem permanecer separados do motor visual da IQ Option.

O modo de tela detecta geometricamente algumas velas verde/vermelho, exibe a região selecionada e descreve somente movimento **visual relativo**. Não consegue obter preços, horários de negociação ou vencimentos oficiais dos pixels; por isso a tela mantém **AGUARDAR** e exibe estruturas técnicas estimadas, sem entrada validada. Não alimenta o simulador como se fossem cotações reais.

## Monitor visual otimizado (v1.7)

A aba **Tela ao vivo** agora usa uma arquitetura de captura desacoplada
do processamento. O callback Windows Graphics Capture copia o quadro
e o coloca em fila de capacidade **um**, enquanto uma thread separada
extrai candles e estruturas. Se a análise atrasar, quadros intermediários
são descartados em vez de acumular demora crescente.

- Captura solicitada a cada **550 ms** (limite desejado, não FPS garantido).
- Leitura HSV vetorizada com NumPy no Windows; fallback Python mantido.
- Prévia reduzida, sem recalcular Text/guard temporal em todos os frames.
- Botão **Parar** não aguarda processamento pesado na thread do Tkinter.
- Sem novos quadros por mais de três segundos, exibe **LEITURA ATRASADA**
  e mantém **AGUARDAR**, sem hipótese operacional válida.
- Capture apenas a região de candles, sem menus ou barra do navegador,
  para reduzir custo e melhorar a legibilidade.

**Importante:** a câmera de pixels ainda não comprova horários/cotações
nem gera sinais M1 validados. Os testes de desempenho são de engenharia
e não demonstram qualidade preditiva ou lucro.

## Dashboard DS Trader 1.6 — nova navegação e painel Forex

A interface Windows foi redesenhada conforme o modelo visual fornecido:
barra lateral com oito páginas, cabeçalho de ações, filtros Forex organizados
no topo, gráfico central e cartões **Próxima vela, Tendência, LTA/LTB e
Suporte/Resistência** na lateral direita. O rodapé acompanha o estado da
fonte e da conexão.

A **Visão geral** contém atalhos funcionais. Importação de CSV, reprodução,
exportação de relatório, backup e monitoramento visual foram preservados.
Sem chave Twelve Data ou com dados atrasados, o Forex mostra AGUARDAR.
A grade ilustrativa não representa cotações reais.

Veja [estrutura, operações e testes do dashboard](docs/DASHBOARD_1_6.md).

## Interface moderna DS Trader 1.4

A guia **Tela ao vivo** ganhou um painel escuro de duas colunas: **previsualizacao do grafico a esquerda** e estado **AGUARDAR**, padroes, LTA/LTB e explicacao a direita. O tema das outras abas tambem foi modernizado, mantendo o software nativo do Windows sem exigir nova biblioteca de interface.

### Fixar a janela do grafico (Windows 10/11)

Na versao 1.4, clique em **Fixar janela do grafico**, arraste uma area
**dentro da janela do aplicativo IQ Option ou navegador** e clique **Iniciar análise**. O DS Trader
identifica a janela escolhida e passa a captar a area relativa a ela com a
API Windows Graphics Capture, mesmo que outra janela fique na frente. Assim
nao aparece o efeito de recursao com o DS Trader capturando a propria tela.

Mantenha a janela de origem **aberta e não minimizada**. A captura não
garante atualizacao quando a aplicacao para de desenhar quadros, quando a
janela e minimizada ou em casos de protecao de conteudo. Se mudar bastante
o tamanho/escala do navegador, selecione novamente. Se a captura falhar,
mostra uma mensagem e interrompe; nao passa automaticamente a capturar o
desktop por cima. A versao fixada nao certifica horario nem preco da IQ Option.

Ao clicar **Fixar janela do grafico**, o DS Trader oculta sua janela temporariamente para que voce selecione uma area dentro da janela do navegador. Depois disso, a previa usa a janela fixada como origem, mesmo quando outra janela fica na frente. Na captura antiga de desktop, sobreposicoes continuam bloqueadas.

O periodo M1/M5/M15 no painel e **informado manualmente**, nao reconhecido automaticamente. O leitor visual nao confirma o momento exato de fechamento da proxima vela e **nao libera CALL/PUT como entrada**.

Consulte [guia do novo painel](docs/INTERFACE.md), [regras tecnicas](docs/SINAIS.md) e [testes](docs/TESTES.md).

## Hipoteses CALL / PUT / AGUARDAR e leitura de padroes (v1.2)

Na aba **Tela ao vivo**, o DS Trader agora pode descrever engolfo, doji,
martelo, inside bar, suporte/resistencia e LTA/LTB por pivos. Exibe uma
hipotese **CALL / PUT / AGUARDAR** com explicacoes. A leitura da tela e
**EXPERIMENTAL**: nao confirma por si o fechamento exato do candle e
nao constitui recomendacao de entrada na IQ Option. Recortes irregulares
ou com menos de 26 possiveis candles resultam em **AGUARDAR**.
A captura exige 3 quadros geometricamente estaveis antes de exibir estruturas estimadas, mas isso nao confirma o fechamento.
LTA/LTB sao desenhadas na previa, quando detectadas.

## Ciclo de teste M1 com prova temporal

O modulo `ds_trader/m1_cycle.py` implementa uma maquina de estados testavel:
**PENDENTE → ATIVA → CONCLUIDA** ou **AGUARDAR**, sem enviar ordens.
Requer ativo/fonte/M1/relogio confirmados, pelo menos 25 candles M1
fechados e consecutivos, preco de abertura com horario exato e preco de
fechamento comprovado 60 segundos depois. Leituras atrasadas ou incertas
invalidam a tentativa. ACERTO/ERRO/EMPATE compara somente os dois precos,
sem prometer lucro ou simular payout.

**Fronteira temporal importante:** se a ultima vela utilizada fecha em T,
uma hipotese so pode ser preparada *depois* de T. Como a vela seguinte ja
abre em T, a primeira abertura elegivel e T+60 segundos. Nao se usa o
fechamento de T para fingir uma decisao anterior a T. O motor M1 esta
disponivel para testes automatizados e futuro adaptador de dados verificados;
a captura de tela e a Twelve Data atuais **nao comprovam a abertura e o
vencimento da IQ Option** e nao ativam ciclos validos desse modulo.

A aba **Forex em tempo real**, se houver chave de API e cotacoes atuais,
tambem exibe uma hipotese da proxima barra, mas troca para AGUARDAR
quando o candle estiver velho demais, mesmo que a serie seja historicamente
valida. Nenhum modo inventa probabilidade de acerto, payout ou horario
de vencimento na corretora.

**Regras detalhadas, validacao e limites:** [Sinais e proxima vela](docs/SINAIS.md).
A estrategia e exploratoria, nao foi validada para operacoes reais.

## Acompanhar o Forex com dados do mercado (v1.1)

A aba **Forex em tempo real** permite consultar candles de **EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, EUR/JPY, EUR/GBP e NZD/USD**, recebidos da **Twelve Data**. E diferente da simulacao sintetica e da leitura visual de tela:

1. Crie conta no fornecedor em https://twelvedata.com/ e obtenha uma **chave de API**, de acordo com o plano disponivel. Nao envie a chave a outra pessoa, nem aqui no chat.
2. No DS Trader, abra **Forex em tempo real**, selecione o par de moedas e intervalo (1, 5 ou 15 minutos).
3. Cole a chave no campo protegido e clique **Conectar ao mercado**.
4. O sistema consulta o endpoint HTTPS de candles do fornecedor, mostra horario de fechamento UTC, indicacao de atraso, grafico OHLC, medias 9/21 e niveis aproximados por pivos. A captura e independente da IQ Option.
5. Ao clicar **Desconectar**, o aplicativo encerra as novas consultas e descarta a chave da memoria do componente.

O intervalo padrao de **120 segundos por consulta** protege a cota gratuita (ate cerca de 720 chamadas por 24 h se deixado ativo continuamente; tarifas e limites dependem do plano). Ha opcoes 60 ou 300 segundos. Isso e **atualizacao periodica**, nao streaming tick-a-tick. A analise exige pelo menos 25 candles consecutivos **ja fechados**. Candle ainda aberto, dados antigos e lacunas sao descartados/identificados; se as cotacoes estiverem atrasadas, nenhuma tendencia atual e calculada. Nao se faz estimativa de duracao, payout, acerto ou sinal operacional CALL/PUT. A API da Twelve Data exige conexao com a internet e pode ter custo.

A chave e usada apenas na consulta da API via HTTPS, nao e salva no SQLite nem em relatórios. Como a API da Twelve Data usa chave por URL, o provedor e a infraestrutura de rede podem ve-la; nao compartilhe o computador com pessoas sem autorizacao. Nenhuma chamada de ordens ou acesso a conta da IQ Option foi implementada. O feed agrega precos de fornecedores: eles **nao sao necessariamente os mesmos precos da sua corretora**, nem garantem negociabilidade ou lucratividade.

Documentacao do provedor: https://twelvedata.com/docs e https://support.twelvedata.com/en/articles/12520817-forex-api-v2

## Monitorar seu gráfico na tela em tempo real (leitura visual)

1. Abra o gráfico em seu navegador/corretora, preferencialmente com fundo escuro e candles verdes/vermelhos visíveis.
2. No DS Trader abra **Monitor**. Clique em **1 Selecionar janela**.
3. Arraste o mouse apenas sobre os candles, sem menus, login ou informações pessoais. Pressione **Esc** para cancelar.
4. Clique em **2 Iniciar monitor**: a captura tenta obter um quadro a cada 550 ms, mas a frequência real depende do Windows, do OCR e do processamento. A prévia é atualizada em ritmo menor e mostra idade dos quadros.
5. Clique em **Parar** a qualquer momento. A captura não começa sozinha; frames são mantidos somente na memória e não são salvos nem transmitidos.

**Limitações:** cores diferentes, linhas/indicadores sobrepostos, janela minimizada, conteúdo protegido, mudanças de escala, lag, velas sobrepostas e monitores com DPI especial podem impedir/alterar a leitura. A última vela é tratada como potencialmente aberta. Não usar esse modo como fonte de preço ou prova de rentabilidade. O modo CSV mantém simulação independente.

## Ciclo M1 de estudo: só com dados temporais comprovados

O módulo `ds_trader/m1_cycle.py` implementa a sequência **hipótese pendente
antes da abertura → cotação de abertura exata → comparação no vencimento
T+60 s**. Exige candles fechados com horário de confirmação e referências
de preços com timestamps, da mesma fonte e do mesmo ativo. Não usa
fechamento futuro e nunca confunde OHLC.open ou o preço do candle anterior
com preço real de referência de entrada. A avaliação ACERTO/ERRO/EMPATE é
apenas de referência, sem ordens nem payout.

**A captura visual da IQ Option não fornece essas provas.** Sua aba mostra
**AGUARDAR** para o ciclo validado e explica por quê, mesmo quando reconhece
padrões, tendência ou LTA/LTB. A API Twelve Data não alimenta automaticamente
o ciclo da IQ Option; fontes são separadas.

Veja as regras, horários e exemplos em
[**Ciclo M1 e critérios de validação**](docs/CICLO_M1.md).
Os testes sintéticos estão em `tests_ds/test_m1_cycle.py`.

## Baixar e instalar no Windows 10/11 (64 bits)

**Página de download:** https://daniel-soliz.github.io/Robo-Das-Binarias/

1. Abra a página e clique em **Baixar instalador**, quando a compilação estiver disponível.
2. Execute **DS-Trader-Setup.exe**, siga o assistente em português e clique em **Concluir**.
3. O instalador cria **DS Trader** na Área de Trabalho e no Menu Iniciar. Depois basta abrir o atalho.
4. Na primeira execução, selecione **Exemplo sintético** e **Iniciar / continuar** para conhecer o programa.

A instalação é feita na pasta do usuário, sem exigir Python nem privilégios de administrador. Inclui desinstalador acessível pelo Windows. O histórico dos estudos é mantido separadamente em `%LOCALAPPDATA%\DS Trader`; desinstalar não exclui automaticamente o histórico.

**Versão portátil opcional:** na mesma página, o link de ZIP só aparece quando houver pacote confirmado. Extraia o ZIP completo e abra `DS-Trader/DS-Trader.exe`. Não separe a pasta `_internal` do executável.

A página consulta os assets da última release pública e **não mostra um botão de download fictício**. O workflow `.github/workflows/testes.yml` testa o motor, empacota, executa teste real de interface no Windows, instala silenciosamente e verifica atalho e execução antes de publicar `DS-Trader-Setup.exe` em Releases versionadas do GitHub. Se a compilação falhar, a página aponta para o estado dos testes, sem oferecer um arquivo inexistente.

O executável e o instalador **não possuem assinatura digital**. O Windows pode exibir avisos; não desative o Defender ou outras proteções para executar o programa. Os testes automatizados usam Windows Server 2022 e não substituem um teste manual no Windows 10/11 pessoal.

## Executar a partir do código

Instale **Python 3.11.9 x64** com Tcl/Tk (distribuição oficial Windows). Na pasta extraída:

```powershell
py -3.11 main.py
```

Para rodar a partir do código com o modo de tela, instale as bibliotecas com `py -3.11 -m pip install -r requirements-runtime.txt` antes de executar. Bibliotecas fixadas: `mss==9.0.2`, `Pillow==11.0.0`, `windows-capture==2.0.1` e suas dependencias Windows fixadas. No instalador Windows ja vêm incluidas. O modo CSV e o núcleo da simulação não precisam de OCR, conta, chave de IA nem banco remoto.

## Gerar o pacote Windows

Em Windows com Python 3.11.9 x64:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pip==24.3.1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

Dependências do build e suas versões estão em `requirements-build.txt`. O script executa testes, empacota com PyInstaller 6.11.1, abre o executável e testa gráfico, simulação, gravação e exportação. Saída: `release-build/DS-Trader-Setup.exe`, `DS-Trader-Windows-x64.zip` e respectivos SHA256. A compilação do assistente usa Inno Setup 6 (versão 6.4.3 no fallback do CI). A compilação é feita em Windows; não se renomeiam arquivos para `.exe`. Não prometemos build bit a bit idêntico: imagem Windows, pip e artefatos upstream podem mudar.

## Dados

CSV UTF-8, vírgula como separador e ponto decimal:

```csv
timestamp,asset,source,market,interval_seconds,open,high,low,close
2025-01-06T09:00:00-03:00,EURUSD,MINHA-FONTE,REGULAR,60,1.03,1.031,1.029,1.0305
```

- `timestamp`: abertura da barra, com fuso. Candles abertos/futuros não são aceitos.
- `market`: `REGULAR` ou `OTC`; nunca misturamos fontes, mercados ou intervalos.
- `volume`: opcional; não é fabricado.
- `open_time`: opcional; **horário observado da cotação `open`**, dentro da barra. Só preencha se comprovado pela fonte. Não copie automaticamente o horário do candle.
- `payout` e `payout_known_at`: opcionais; payout entre 0 e 1, conhecido até `open_time`. Sem ele, usa o cenário hipotético configurado.

Dados OHLC comuns permitem analisar, mas não garantem entrada/vencimento: sem cotações com horários exatos, o resultado é **indeterminado**. A V1 aceita uma cotação explícita de abertura por barra; não importa ticks separados. Expirações fora da grade dessas cotações ficam indeterminadas. Não extrapola, interpola nem substitui a fonte.

Qualquer duplicata, ordem inválida, lacuna, OHLC inconsistente, fuso ausente ou intervalo incorreto **rejeita o arquivo inteiro**, com número de linha. Para sessões separadas por fins de semana/pausas, importe arquivos contínuos separados; não há calendário de pregão automático. Origem e horários declarados não são certificados pelo aplicativo.

## Documentação

- [Manual simples](docs/MANUAL.md)
- [Regras objetivas e parâmetros](docs/ESTRATEGIA.md)
- [Diagnóstico, IQ Option e arquitetura](docs/DIAGNOSTICO.md)
- [Testes executados e limitações](docs/TESTES.md)
- [Documentação antiga preservada](docs/LEGADO.md)

O histórico/configuração ficam em `%LOCALAPPDATA%\DS Trader\history.sqlite3`. Exportação JSON inclui dados importados, SHA256, eventos, operações, versão e parâmetros. CSVs são próprios para planilhas; campos textuais que parecem fórmulas são escapados. Backup é SQLite completo.

## Testes

```powershell
python -m unittest discover -s tests_ds -v
python -m scripts.gui_smoke
```

O segundo comando precisa de ambiente gráfico. O código antigo e seus testes estão preservados; dependências em `requirements-legacy.txt`, entrada antiga `legacy_main.py`. **Não integram a interface nem o executável DS Trader.** Reaproveitamos `data_sources.base.Candle` e `analysis.levels.detectar_pivos`.

Dados sintéticos em `examples/` servem exclusivamente a aprendizado e teste de software. Lucro histórico não valida estratégia. Wilson 95% pressupõe independência, o que operações financeiras podem não ter. Não há previsão probabilística, martingale, otimização automática, IA externa ou ordens reais. A leitura contínua da tela não substitui dados de mercado autenticados.
