---
name: show-me
description: "Prova visual de cada dado ou citação: acha a fonte primária, captura o print da página com o trecho realçado (PDF, site, relações com investidores), monta a ficha de prova (fonte, data, trecho colado, link da matéria, print, nota) e confere tudo com um gate. Use para 'show me', 'mostra a fonte', 'de onde veio esse dado', 'ficha de prova', 'print da fonte', 'fontes do deck', 'caderno de evidências'."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch
---

# Show Me — caderno de evidências visual

## Princípio

Fact-check responde "esse dado bate com a fonte?" (texto). **Show Me responde "me mostra a
fonte"** — entrega a prova material: o print da página original, com o trecho destacado, e o
endereço de onde ela vive. Anti-alucinação por evidência, não por confiança.

- **Consultoria:** o deck que mostra a página real do relatório por trás de um número ganha
  credibilidade na hora.
- **Acadêmico:** prova material de cada citação antes de submeter ou defender.

O ganho maior não é a auditoria: é que, obrigada a abrir cada fonte e colar o trecho de lá, a
própria IA encontra erros que ela mesma cometeu.

## Quando não usar

Verificação só textual, sem print, é fact-check comum. Só baixar um paper é trabalho de
gerenciador de referências.

## Antes de executar

O gargalo é **rede, não raciocínio**. Nunca baixe em série o que dá para baixar em paralelo, e
nunca rebaixe o que já está no cache. Paralelizar não custa qualidade: o print é idêntico.

## Pipeline

### Fase 1 — Extrair os alvos

Do documento (`.docx` via python-docx, `.pdf` via pymupdf) extrair a lista de
`(afirmação, autor, ano, dado)`. Sem alvo específico, pegar todas as referências e os dados
quantitativos. **Priorize dado com número** — é onde o print prova alguma coisa. Referência
puramente teórica vai para uma seção-lista com DOI ou ISBN, sem print obrigatório.

### Fase 2 — Resolver as fontes, em cascata e em paralelo (artigo científico)

Para cada alvo, resolva o PDF na primeira camada que responder, e dispare todos os alvos em
paralelo (`xargs -P 6` ou jobs em background):

1. **Cache local** — `~/.cache/show-me/sources/<slug>.pdf`, de execuções anteriores.
2. **O que você já tem** — procure no disco por autor e título antes de ir à rede
   (`find ~ -iname "*<autor>*.pdf"`). Quem trabalha com um corpus já baixou metade dele.
3. **Rede, via `scripts/fetch_pdf.py`** — cascata aberta Crossref → Unpaywall → OpenAlex →
   arXiv, gravando no cache:

```bash
python3 scripts/fetch_pdf.py --doi 10.1002/smj.4057 --email voce@exemplo.com
python3 scripts/fetch_pdf.py --title "Dynamic capabilities and strategic management"
```

4. **URL direta**, quando você já sabe onde está (arXiv, NBER, repositório institucional).

**Paywall sem via aberta:** marque *"fonte não localizável visualmente"* e registre o DOI.
Nunca fabrique print nem URL. Plataforma paga (Gartner, Scopus, Web of Science) não recebe
crawler — use o export nativo dela.

**Confira o que baixou.** O fallback de busca por título erra: um PDF de 1.800 páginas pode
chegar no lugar de uma revisão de 20. Case a primeira página com o título antes de usar.

### Fase 2b — Empresa, regulador e imprensa (deck de consultoria, caso de empresa)

A cascata acima é de paper. Um caso de empresa pede outra ordem:

1. **Relações com investidores**: release de resultados e apresentação institucional. Em muitos
   sites o PDF tem URL estável e aceita `#page=N` — esse é o `link` da ficha. Diagnóstico de um
   trimestre ruim sai do release **daquele** período, não de memória.
2. **Regulador e ranking público**: o órgão do setor, o banco central, a comissão de valores, o
   ranking da associação. PDF com página; o print pela `scripts/prova-print-pdf.py`.
3. **Imprensa e blog que citam o regulador**: `scripts/prova-print-web.py`. Ele esconde anúncio,
   overlay e barra fixa e busca o termo **só em parágrafo, item ou célula** — senão o print sai
   com a propaganda no lugar do número, o que já aconteceu. Fonte secundária se declara na `nota`
   e se cruza com o primário quando ele existe.
4. **Site com Cloudflare ou Turnstile**: `--headed` sob `xvfb-run -a`, com Chrome real. Alguns
   sites não passam nem assim.
5. **Print pedido ao usuário**: camada legítima quando 1 a 4 falham. A ficha diz "lido pelo autor
   em dd/mm/aaaa" e explica por que não há captura. Peça cedo e siga trabalhando no resto.
6. **Dado próprio** (raspagem, pesquisa do grupo): a ficha aponta o arquivo bruto e o script, e
   declara universo e cobertura ("1.665 de 10.156 registros, 16%"). Amostra tem nome de amostra.

### Fase 3 — Localizar o dado e capturar

- **Busca tolerante:** o mesmo dado aparece como `47%`, `47 percent` ou `0.47`; milhar como
  `5,179`, `5179` ou `5.179`. Prefira a página com melhor match (abstract ou figura antes de
  menção solta).
- **Print é o dado, não a página.** Recorte em volta do realce, com a frase inteira de contexto.
  Quando o número repete, escolha a ocorrência (`"49%:2"`). **Print sem realce não é print**: o
  script marca `SEM DESTAQUE`, grava com sufixo `_semdestaque`, e o gate barra.
- **Número dentro de figura rasterizada:** não está no texto. Use `--ocr` (pede `pytesseract`)
  ou capture a figura inteira — e diga que é captura, não busca.

```bash
python3 scripts/prova-print-pdf.py fonte.pdf 28 saida.jpg "0,7" "13.857"
python3 scripts/prova-print-web.py alvos.json provas_print/ [--headed]
python3 scripts/highlight.py fonte.pdf --find "47%" "47 percent" --out prova.jpg
```

Os dois primeiros gravam um `saida.jpg.txt` ao lado do print, com o texto da página ou do
parágrafo em volta do realce. É esse arquivo que o gate usa para conferir o trecho.

### Fase 4 — Cross-check e montar o caderno

- **O cross-check é o produto principal, não uma nota de rodapé.** Leia a frase inteira em volta
  do realce antes de citar e registre "a fonte diz X, o texto dizia Y" como item de primeira
  classe. Num deck recente foi assim que apareceram nove números errados: um percentual atribuído
  à empresa errada, um prazo que a fonte já tinha retirado, uma data um ano fora.
- **O trecho da ficha se cola do texto extraído por código, nunca se digita.** Serve o sidecar
  `.jpg.txt`, o `pdftotext` da página, ou o texto que o usuário colou da fonte. O que não serve é
  reescrever de memória.
- **`link` é a matéria ou a página específica**, campo separado do `url` descritivo; em PDF, com
  `#page=N`. Link montado a partir do texto descritivo leva ao domínio, não ao dado.
- **Uma ficha, dois modos de saída.** A ficha é um dicionário
  `{chave: {fonte, data, claim, trecho, url, link?, print?, nota?, lido_por?}}` (em `provas.json`,
  ou em `provas.py` com `PROVAS`), e os dois modos leem dele:
  1. **Caderno à parte** — `.docx` ou `.pdf`, um bloco por evidência: afirmação → fonte →
     localização → print destacado → nota ou divergência. Seção final com as referências
     teóricas.
  2. **Embutido no artefato** — marcador `[n]` no texto, ficha no hover, rodapé "Fontes [n]
     Veículo" com link em toda página, página final com todas, print em base64. Prefira HTML a
     PowerPoint: o hover e o link só existem em HTML. Se o artefato é editável pelo leitor, leia
     as edições dele antes de reconstruir — republicar por cima apaga a revisão.

Feche com o gate:

```bash
python3 scripts/prova-gate.py provas.py --prints provas_print/ [--usadas deck.html]
```

Ele confere, ficha a ficha: campos obrigatórios, print existente e com realce, trecho contido no
texto capturado, `link` que é URL, e nota obrigatória quando não há print. Sai 1 se qualquer uma
falhar, e diz quantas conferiu — nunca dá sucesso em conjunto vazio.

## Três regras que vieram de erro real

1. **Cada trecho citado é conferido por código antes de montar.** Carregue o texto por página do
   PDF, normalize hífen de quebra e ligadura, e **falhe** se a literal não estiver na página
   declarada. Tradução vai ao lado da literal, nunca no lugar dela. Sem isso sai "p. 545" num
   caderno entregue quando era p. 544: PDF de base de dados costuma ter capa, e a paginação do
   arquivo não é a paginação impressa.
2. **Tabela de cobertura no fim: fonte citada → onde está o print.** Extraia por código toda
   referência das colunas de fonte e das notas, compare com os blocos de print, e liste o que
   ficou sem print **com a razão** (PDF não localizado, dado próprio, decisão do autor). Um
   caderno de 30 páginas já foi entregue com onze fontes sem prova, e não havia como notar.
3. **Teto de 4 MB por arquivo HTML entregue.** Print em JPEG, largura 1000 px, qualidade 70,
   nunca PNG. Acima de 4 MB, divida por bloco: arquivo 0 com estrutura, resumo, lacunas e
   cobertura; arquivos 1..N com os prints e links cruzados. A contagem de blocos dentro do
   arquivo não prova entrega — o que o leitor vê na tela prova.

Para ler no papel ou num leitor e-ink: converta com `google-chrome --headless=new
--print-to-pdf` e `@page A4` injetado, e valide o número de páginas com `pdfinfo` antes de
mandar. Navegador em sandbox às vezes renderiza um PDF longo como página única.

## Os scripts

| Script | Faz | Sai 1 quando |
|---|---|---|
| `scripts/fetch_pdf.py` | resolve o PDF do artigo por DOI ou título, em cascata aberta | não achou via aberta |
| `scripts/highlight.py` | acha o termo no PDF e renderiza a página com destaque | termo não encontrado |
| `scripts/prova-print-pdf.py` | print de página de PDF, termos realçados e recortados, mais o sidecar de texto | algum termo não foi achado |
| `scripts/prova-print-web.py` | print de página web, anúncio escondido, termo em parágrafo, mais o sidecar | nunca; grava `_semdestaque` para o gate barrar |
| `scripts/prova-gate.py` | confere as fichas contra os prints e o texto capturado | qualquer ficha falha, ou o conjunto é vazio |

**Esta skill não depende de nenhuma outra.** Se você tiver uma skill de download de papers, de
fact-check ou de apresentações, elas compõem bem: esta entra como a camada visual.

## Dependências

```
pip install pymupdf requests pillow playwright
pip install pytesseract                # opcional, só para número dentro de figura
```

`prova-print-pdf.py` usa o `pdftotext` do poppler (`apt install poppler-utils`) e
`prova-print-web.py` pede um Chrome real (`playwright install chrome`). Passo a passo no
`ONBOARDING.md` do plugin.

## Saída

`ShowMe-<documento>_vN.{pdf,docx}`, salvo junto da origem, seguindo a convenção `_vN`.

## Limites (honestos)

- Número em figura rasterizada: OCR é mais frágil; capturar a figura inteira é mais honesto.
- Paywall sem via aberta: marque como não localizável e registre o DOI. Nunca fabrique a prova.
- Site com proteção antibot forte: peça o print ao usuário e declare isso na ficha.
