# show-me

Uma skill para o Claude Code e o Claude Cowork: **cada dado do texto sai com a prova junto**.

Para cada numero, citacao ou afirmacao, a skill acha a fonte primaria, captura o print da
pagina com o trecho destacado em amarelo e monta uma ficha de prova — de onde veio, quem
publicou, quando, o trecho literal e o link para a pagina exata. No documento final, passar
o mouse sobre a citacao abre essa ficha.

O ganho nao e so de auditoria. Obrigada a abrir cada fonte e a colar o trecho de la, a
propria IA encontra e corrige erros que ela mesma cometeu: numero trocado, link morto, data
errada, citacao que a fonte nao sustenta.

## Instalar

No **Claude Code**:

```
/plugin marketplace add flaviomkpies/show-me
/plugin install show-me@show-me
```

No **Claude Cowork**: Personalizar, Plugins, Adicionar, Adicionar marketplace, Adicionar de
um repositorio, e colar `flaviomkpies/show-me`. Deixe ligado o "Atualizar automaticamente"
para receber as versoes novas.

## Antes do primeiro uso

Leia o **`plugins/show-me/ONBOARDING.md`**. Sao tres minutos: duas bibliotecas Python
(`pymupdf` e `requests`) e um e-mail de contato para as APIs abertas de artigo cientifico.

## Usar

```
show-me neste relatorio
```

Ou, dentro de um pedido maior: "escreva a secao e passe o show-me em cada numero".

## Licenca

MIT (`LICENSE`). Use, modifique e redistribua como achar melhor. Se ajudou, uma estrela no
repositorio ajuda outras pessoas a encontrar a skill.
