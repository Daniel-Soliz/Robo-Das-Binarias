# Robô das Binárias — análise técnica em diagnóstico (Etapa 3)

Aplicação Python para **observar gráficos** de Forex na IQ Option. O objetivo final é emitir alertas de decisão manual; as Etapas 2 e 3 capturam dados e calculam confluência teórica, ainda sem alertas operacionais. O software **não executa operações, não clica na plataforma, não movimenta dinheiro e não envia ordens**. Ativos identificados como OTC são ignorados.

## Instalação — Windows 10/11

1. Instale Python 3.11 e o executável **Tesseract OCR**. Inclua o diretório do Tesseract no `PATH` e confirme no PowerShell com `tesseract --version`.
2. Clone ou baixe este repositório e abra o terminal na sua raiz.
3. Execute:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --modo tela
```

### Primeira calibração

Com o gráfico aberto e visível:
1. No primeiro seletor de tela, arraste uma área que inclua **somente a região das velas**, evitando botões, indicadores e rótulos.
2. No segundo seletor, selecione a área que exibe **o ativo e o timeframe M5 ou M15** simultaneamente.
3. Confira no terminal o ativo, período e número de candles reconhecidos.
4. Pressione `Ctrl+C` no terminal para encerrar.

O arquivo pessoal `config.json` é gerado automaticamente e fica **fora do controle de versão**. Para repetir, execute `python main.py --recalibrar`. Parâmetros de FPS, intervalos e regiões estão em `config.example.json` e podem ser personalizados no `config.json`.

**Limitações desta etapa:** o Modo A reconhece aproximadamente velas verdes/vermelhas por cor. Cores não padronizadas, corpos muito estreitos, candles sobrepostos, zoom, indicadores visuais e mudança de escala podem causar erros. Os OHLCs extraídos da imagem são **relativos entre 0 e 1**, sem preços ou timestamps históricos garantidos. O gráfico M5 sozinho não fornece uma série M15 verificável; não há geração de sinais. Se OCR falhar ou detectar OTC, a análise para. A captura deve ser validada na sua própria máquina; não foi feita validação prática na IQ Option a partir deste ambiente.

## Modo B — API experimental e não oficial

A biblioteca comunitária [iqoptionapi](https://github.com/iqoptionapi/iqoptionapi) **não é oficial** e sua compatibilidade com versões atuais da plataforma não é garantida. A documentação alerta que `get_candles` pode atrasar cerca de **30 segundos**. Portanto, ela **não deve ser tratada como uma fonte confiável para expiração de 1 minuto**. Usar somente **conta DEMO**.

Opcionalmente instale via Git (pode apresentar conflitos por ser biblioteca antiga):

```powershell
python -m pip install "git+https://github.com/iqoptionapi/iqoptionapi.git"
```

Depois copie `.env.example` para `.env`, preencha `IQ_EMAIL` e `IQ_PASSWORD` **somente localmente** e, após conferir o uso de conta DEMO, configure `IQ_CONTA_DEMO_CONFIRMADA=SIM`. Ajuste `api_ativo` em `config.json` (ex.: `EURUSD`), nunca um ativo OTC. Execute:

```powershell
python main.py --modo api
```

O adaptador utiliza somente `connect`, `check_connect` e `get_candles`. **Não verifica nem altera automaticamente o tipo da conta**; cabe ao operador assegurar que é DEMO. Existe reconexão com espera progressiva e rejeição de dados inválidos. A rede, o login e a API não foram validados ao vivo nesta etapa.

## Testes

```powershell
python -m pytest -q
```

A suíte cobre contrato/configuração, regra OTC, identificação OCR por texto simulado, velas coloridas sintéticas e normalização de candles simulados da API. Há workflow para Windows e Linux no GitHub Actions. Testes de indicadores e confluência serão adicionados na Etapa 3.

## Segurança e aviso de risco

- `.env`, `config.json`, logs, capturas e CSVs locais são ignorados pelo Git; jamais publique credenciais.
- A captura não realiza cliques, digitação ou comandos na IQ Option.
- OCR incerto, OTC e histórico insuficiente não produzem recomendações.
- Opções binárias e digitais apresentam alto risco de perda. Nenhuma ferramenta garante acertos ou rentabilidade.

## Etapa 3 — motor de análise M5/M15 (somente diagnóstico)

Implementações na pasta analysis/:
- indicators.py: EMA 9/21/50 e RSI 14 de Wilder; aquecimento explícito.
- patterns.py: engolfos, haramis, martelos, enforcado, doji, pin bars, estrelas e três soldados/corvos.
- levels.py: pivôs confirmados, zonas de reação e quantidade de toques.
- trendlines.py: LTA/LTB com inclinação, contatos, toque, rompimento ou reteste.
- signal_engine.py: pontuação M15 (25), zona (20), padrão (20), linha (15), EMA (10), RSI (10).
- session.py: agrupa M5/M15 do mesmo ativo e da mesma fonte sem misturar mercados.

### Sinais operacionais desabilitados

Não existe comando ou opção de configuração capaz de habilitar sinais reais nesta etapa.
O resultado operacional é sempre False, validade_segundos sempre 0, sem alerta sonoro, clique, compra, venda ou envio de ordens.
Se todos os filtros forem satisfeitos, o terminal pode exibir apenas CANDIDATO TEÓRICO — NÃO OPERACIONAL.
Os dados extraídos pela tela têm valores normalizados, sem preço e tempo histórico confiáveis: o Modo A permanece AGUARDAR.
A API comunitária é não oficial e pode atrasar; seu diagnóstico nunca representa autorização de entrada.
A nota 100/100 representa confluência, NÃO probabilidade medida de acerto.

### Testar

Execute python -m pytest -q. São testados indicadores, padrões, zonas, tendência, pontuação e bloqueios.
Para personalizar a pontuação altere pontuacao_minima no config.json (50–100; padrão 75). Isso não libera sinais.
A leitura real em Windows e sua consistência ainda exigem validação presencial; a expiração de um minuto ainda não foi validada.
