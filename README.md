# DS Trader — Análise e Simulação

Aplicativo desktop em português para estudar **rompimento e reteste**. Importa CSV, mostra candles e regiões, reproduz cronologicamente, explica eventos, simula e exporta resultados. Também inclui um **modo de leitura visual contínua da tela**, opt-in, sem upload de fotos. **Não envia ordens nem conecta à corretora.**

O modo de tela detecta geometricamente algumas velas verde/vermelho, exibe a região selecionada e descreve somente movimento **visual relativo**. Não consegue obter preços, horários de negociação ou vencimentos oficiais dos pixels; por isso a tela mantém **AGUARDAR** e exibe estruturas técnicas estimadas, sem entrada validada. Não alimenta o simulador como se fossem cotações reais.

## Interface moderna DS Trader 1.4

A guia **Tela ao vivo** ganhou um painel escuro de duas colunas: **previsualizacao do grafico a esquerda** e estado **AGUARDAR**, padroes, LTA/LTB e explicacao a direita. O tema das outras abas tambem foi modernizado, mantendo o software nativo do Windows sem exigir nova biblioteca de interface.

### Fixar a janela do grafico (Windows 10/11)

Na versao 1.4, clique em **Fixar janela do grafico**, arraste uma area
**dentro da janela do navegador** e clique **Iniciar analise**. O DS Trader
identifica a janela escolhida e passa a captar a area relativa a ela com a
API Windows Graphics Capture, mesmo que outra janela fique na frente. Assim
nao aparece o efeito de recursao com o DS Trader capturando a propria tela.

Mantenha a janela do navegador **aberta e nao minimizada**. A captura nao
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
2. No DS Trader abra a guia **Tela ao vivo**. Clique em **Fixar janela do gráfico**.
3. Arraste o mouse apenas sobre os candles, sem menus, login ou informações pessoais. Pressione **Esc** para cancelar.
4. Clique em **Iniciar monitoramento**: a cada aproximadamente 1,2 segundo o aplicativo atualiza uma prévia e a observação aproximada de direção visual.
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
