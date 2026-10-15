# Robô das Binárias — assistente de leitura (Etapa 2)

Projeto Python para **observação e alerta manual** em gráficos de Forex da IQ Option. **Não executa trades, não clica na plataforma e não envia ordens.** Ativos identificados como OTC são ignorados. A análise técnica e o overlay completo serão implementados nas etapas 3 e 4.

## Executar no Windows

1. Instale Python 3.11 ou 3.12 e o executável Tesseract OCR (inclua no PATH do Windows).
2. Em PowerShell, execute:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python main.py --modo tela
   ```
3. Selecione a região do gráfico e depois a região com nome do ativo/timeframe. Use **Esc** para cancelar. A configuração local fica em `config.json` (ignorada pelo Git).
4. O terminal mostrará os estados de leitura. Use `python main.py --recalibrar` para alterar a área.

**Não confunda coordenadas relativas [0,1] das velas com preço real.** Ainda não há sinal operacional nesta etapa. É necessário validar a captura na própria máquina; sem nome/timeframe OCR confirmados, o programa suspende a leitura.

## Alternativa API, somente leitura (experimental)

A biblioteca `iqoptionapi` é uma dependência **não oficial**, de terceiros, potencialmente instável. Instale-a separadamente e use apenas **conta DEMO**. Copie `.env.example` para `.env`, defina `IQ_EMAIL` e `IQ_PASSWORD` localmente (nunca faça commit), configure `api_ativo` e execute `python main.py --modo api`.

## Testar

```powershell
pytest -q
```

Testes sintéticos avaliam configurações, candles, OCR e segmentação. Para testar o Modo A real é necessário Windows com a janela da plataforma aberta, gráfico visível e cores compatíveis. Não existe garantia de leitura correta em qualquer resolução, tema, layout ou zoom. M5 e M15 simultâneos pela tela requerem histórico validado; não são inventados.

## Segurança e risco

Operações digitais/binárias podem resultar na perda integral do valor investido. Este programa não recomenda nem garante lucros. A informação visual pode estar incompleta, atrasada ou incorreta; não use sem validação extensiva em ambiente demonstrativo.
