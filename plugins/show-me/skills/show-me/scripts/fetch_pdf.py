#!/usr/bin/env python3
"""Resolve um paper em PDF pela cascata aberta Crossref -> Unpaywall -> OpenAlex -> arXiv.

Uso:
    python3 fetch_pdf.py --doi 10.1002/smj.4057 --email voce@exemplo.com
    python3 fetch_pdf.py --title "Dynamic capabilities and strategic management"

Grava em ~/.cache/show-me/sources/<slug>.pdf e imprime o caminho. Se ja existe, nao rebaixa.
Sem chave de API: Unpaywall e OpenAlex so pedem um e-mail de contato (--email ou a variavel
SHOW_ME_EMAIL), que e a etiqueta de polidez das duas.
"""
import argparse
import difflib
import os
import pathlib
import re
import sys
import urllib.parse

import requests

CACHE = pathlib.Path(os.environ.get("SHOW_ME_CACHE", "~/.cache/show-me/sources")).expanduser()
UA = {"User-Agent": "show-me/1.0 (caderno de evidencias)"}


def slug(s, n=60):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")[:n] or "fonte"


def baixar(url, destino):
    try:
        r = requests.get(url, headers=UA, timeout=60, allow_redirects=True)
    except requests.RequestException as e:
        print(f"  falhou {url[:60]}: {e}", file=sys.stderr)
        return False
    if r.status_code != 200 or not r.content[:5].startswith(b"%PDF"):
        print(f"  nao e PDF ({r.status_code}) {url[:60]}", file=sys.stderr)
        return False
    destino.write_bytes(r.content)
    return True


def doi_por_titulo(titulo, email):
    try:
        r = requests.get("https://api.crossref.org/works", headers=UA, timeout=30,
                         params={"query.bibliographic": titulo, "rows": 1, "mailto": email})
    except requests.RequestException:
        return None, None
    itens = r.json().get("message", {}).get("items", []) if r.ok else []
    if not itens:
        return None, None
    it = itens[0]
    return it.get("DOI"), (it.get("title") or [""])[0]


def urls_pdf(doi, email):
    """Candidatos a PDF aberto, em ordem de confianca."""
    out = []
    try:
        r = requests.get(f"https://api.unpaywall.org/v2/{doi}", params={"email": email},
                         headers=UA, timeout=30)
        if r.ok:
            d = r.json()
            for loc in [d.get("best_oa_location")] + (d.get("oa_locations") or []):
                if loc and loc.get("url_for_pdf"):
                    out.append(loc["url_for_pdf"])
    except requests.RequestException:
        pass
    try:
        r = requests.get(f"https://api.openalex.org/works/doi:{doi}",
                         params={"mailto": email}, headers=UA, timeout=30)
        if r.ok:
            d = r.json()
            for loc in [d.get("best_oa_location")] + (d.get("locations") or []):
                if loc and loc.get("pdf_url"):
                    out.append(loc["pdf_url"])
    except requests.RequestException:
        pass
    return list(dict.fromkeys(u for u in out if u))


def url_arxiv(titulo):
    q = urllib.parse.quote(f'ti:"{titulo}"')
    try:
        r = requests.get(f"http://export.arxiv.org/api/query?search_query={q}&max_results=1",
                         headers=UA, timeout=30)
    except requests.RequestException:
        return None
    m = re.search(r"<id>http[^<]*abs/([^<]+)</id>", r.text) if r.ok else None
    return f"https://arxiv.org/pdf/{m.group(1)}" if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doi")
    ap.add_argument("--title")
    ap.add_argument("--email", default=os.environ.get("SHOW_ME_EMAIL", ""))
    ap.add_argument("--out")
    ap.add_argument("--strict", action="store_true",
                    help="falha se o titulo achado divergir do pedido")
    a = ap.parse_args()
    if not (a.doi or a.title):
        ap.error("passe --doi ou --title")
    if not a.email:
        ap.error("Unpaywall e OpenAlex pedem um e-mail de contato: --email voce@exemplo.com "
                 "ou export SHOW_ME_EMAIL=voce@exemplo.com")

    doi, titulo = a.doi, a.title
    if not doi:
        doi, achado = doi_por_titulo(titulo, a.email)
        if not doi:
            print("titulo nao resolveu em DOI no Crossref", file=sys.stderr)
            return 1
        # Busca por titulo erra com facilidade: "Attention is all you need" devolve
        # "Is Attention All You Need?", que e outro paper. Compare antes de confiar.
        parecido = difflib.SequenceMatcher(None, titulo.lower(), (achado or "").lower()).ratio()
        if parecido < 0.9:
            print(f"\n  ATENCAO: o titulo achado nao e o que voce pediu ({parecido:.0%} de "
                  f"semelhanca)\n    pedido: {titulo}\n    achado: {achado}\n"
                  f"  Confira a primeira pagina do PDF antes de usar como prova.\n",
                  file=sys.stderr)
            if a.strict:
                print("--strict: parando aqui.", file=sys.stderr)
                return 1
        else:
            print(f"Crossref: {doi}  ({(achado or '')[:70]})", file=sys.stderr)
        titulo = achado or titulo

    destino = pathlib.Path(a.out) if a.out else CACHE / f"{slug(titulo or doi)}.pdf"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 1024:
        print(destino)
        return 0

    for url in urls_pdf(doi, a.email):
        print(f"  tentando {url[:70]}", file=sys.stderr)
        if baixar(url, destino):
            print(destino)
            return 0
    if titulo:
        u = url_arxiv(titulo)
        if u and baixar(u, destino):
            print(destino)
            return 0

    print(f"sem via aberta para {doi}. Marque 'fonte nao localizavel visualmente' e registre o "
          f"DOI; nunca fabrique o print.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
