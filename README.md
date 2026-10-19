# DS Trader — Análise e Simulação

Aplicativo desktop local em português para estudar **rompimento e reteste**. Importa CSV, mostra candles e regiões, reproduz cronologicamente, explica eventos, simula e exporta resultados. **Não envia ordens nem conecta à corretora.**

## Baixar e instalar no Windows 10/11 (64 bits)

**Página de download:** https://daniel-soliz.github.io/Robo-Das-Binarias/

1. Abra a página e clique em **Baixar instalador**, quando a compilação estiver disponível.
2. Execute **DS-Trader-Setup.exe**, siga o assistente em português e clique em **Concluir**.
3. O instalador cria **DS Trader** na Área de Trabalho e no Menu Iniciar. Depois basta abrir o atalho.
4. Na primeira execução, selecione **Exemplo sintético** e **Iniciar / continuar** para conhecer o programa.

A instalação é feita na pasta do usuário, sem exigir Python nem privilégios de administrador. Inclui desinstalador acessível pelo Windows. O histórico dos estudos é mantido separadamente em `%LOCALAPPDATA%\DS Trader`; desinstalar não exclui automaticamente o histórico.

**Versão portátil opcional:** na mesma página, o link de ZIP só aparece quando houver pacote confirmado. Extraia o ZIP completo e abra `DS-Trader/DS-Trader.exe`. Não separe a pasta `_internal` do executável.

A página consulta os assets da última release pública e **não mostra um botão de download fictício**. O workflow `.github/workflows/testes.yml` testa o motor, empacota, executa teste real de interface no Windows, instala silenciosamente e verifica atalho e execução antes de publicar `DS-Trader-Setup.exe` na release `v1.0.0`. Se a compilação falhar, a página aponta para o estado dos testes, sem oferecer um arquivo inexistente.

O executável e o instalador **não possuem assinatura digital**. O Windows pode exibir avisos; não desative o Defender ou outras proteções para executar o programa. Os testes automatizados usam Windows Server 2022 e não substituem um teste manual no Windows 10/11 pessoal.

## Executar a partir do código

Instale **Python 3.11.9 x64** com Tcl/Tk (distribuição oficial Windows). Na pasta extraída:

```powershell
py -3.11 main.py
```

O aplicativo usa somente a biblioteca padrão. Não requer OCR, conta, chave de IA, banco remoto ou pacote pip para executar pelo código.

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

Dados sintéticos em `examples/` servem exclusivamente a aprendizado e teste de software. Lucro histórico não valida estratégia. Wilson 95% pressupõe independência, o que operações financeiras podem não ter. Não há previsão probabilística, martingale, otimização automática, IA externa ou ordens reais.
