# Instalador autônomo Windows — DS Trader

## Objetivo

O usuário baixa e instala um único `DS-Trader-Setup.exe`, recebe atalhos e abre
o DS Trader com dois cliques, sem instalar Python, bibliotecas ou Tesseract
separadamente. Ao abrir, o Radar M5 apresenta os favoritos e inicia as fontes
públicas disponíveis em segundo plano. Informação sem fonte ou atrasada não vira
cotação fictícia nem alerta operacional.

## Abordagens avaliadas

- **PyInstaller + Inno Setup existente (escolhida):** reutiliza o build Windows,
  incorpora o executável e os dados do OCR no pacote e verifica o instalador;
  mantém a menor alteração de arquitetura.
- MSIX: integra-se ao Windows, mas exige nova identidade e fluxo de assinatura;
  maior retrabalho nesta etapa.
- Instalação manual de Python/Tesseract: não atende à experiência solicitada.

## Escopo

1. Iniciar na página Radar em M5, sem bloquear a interface durante consultas.
2. Incluir binário Tesseract e `eng.traineddata` no artefato Windows via build,
   com resolução explícita do caminho no aplicativo congelado.
3. Falhar o build se OCR essencial estiver ausente, em vez de entregar um Setup
   que promete identificação automática mas não a realiza.
4. Preservar caminhos de dados de usuário, simulações e proteção AGUARDAR.
5. Testes locais para roteamento OCR e preferências iniciais; build, GUI e OCR
   executável reais deverão ser validados em runner Windows.

## Fora do escopo imediato

Contas/chaves pagas de mercado; preços Forex sem licença; equivalência de dados
externos com a IQ Option; ordens automáticas; licenciamento comercial e
assinatura digital do instalador. Na ausência de API Forex configurada, o Radar
marca SEM FONTE; símbolos cripto podem iniciar via provedores públicos.

## Restrições

Distribuição futura precisa revisar licenças dos binários OCR e fornecedores de
dados, além de assinatura de código. Setup não embute credenciais. O ambiente
atual Linux não compila ou valida executáveis Windows; o pipeline remoto já
existente se responsabiliza por isso quando executado.
