# -*- coding: utf-8 -*-
"""Gate das fichas de prova . Sai 1 se qualquer ficha falhar; diz quantas conferiu.

Uso: python3 prova-gate.py provas.json|provas.py [--prints DIR] [--usadas deck.html]
     --usadas: confere só as chaves que o HTML referencia (data-k="chave"); as demais são rascunho

Confere, por ficha:
  campos      fonte, data, claim, trecho, url presentes
  print       o arquivo existe em DIR e não é *_semdestaque (print sem realce não é prova)
  trecho      se existe DIR/<print>.jpg.txt (gravado pelos prova-print-*), o trecho da ficha está nele,
              normalizado (espaço, hífen de quebra, aspas). É o gate contra o trecho digitado: em 19/09
              o 13% era da Allianz e não da Tokio, e "7 dias úteis" tinha sido retirado pela fonte.
  link        se existe, começa com http
  sem print   precisa de `nota` dizendo por quê (Turnstile, lido pelo usuário, dado próprio)
A ficha é um dict {chave: {fonte, data, claim, trecho, url, link?, print?, nota?}} em JSON, ou um
módulo Python com PROVAS = {...}.
"""
import sys, json, pathlib, re, unicodedata, importlib.util

def carrega(p):
    p = pathlib.Path(p)
    if p.suffix == ".json": return json.loads(p.read_text())
    spec = importlib.util.spec_from_file_location("provas", p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.PROVAS

def norm(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = t.replace("-\n", "").replace("­", "")
    t = re.sub(r"[\"'“”‘’«»]", "", t)
    return re.sub(r"\s+", " ", t).strip().lower()

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    provas = carrega(sys.argv[1])
    if "--usadas" in sys.argv:
        html = pathlib.Path(sys.argv[sys.argv.index("--usadas") + 1]).read_text(errors="ignore")
        usadas = set(re.findall(r'data-k="([^"]+)"', html))
        provas = {k: v for k, v in provas.items() if k in usadas}
        for k in usadas - set(provas): print("  FAIL", f"{k}: o deck referencia uma ficha que não existe")
    prints = pathlib.Path(sys.argv[sys.argv.index("--prints") + 1]) if "--prints" in sys.argv else pathlib.Path(sys.argv[1]).parent / "provas_print"
    falhas, conferidas_trecho = [], 0
    for k, d in provas.items():
        for c in ("fonte", "data", "claim", "trecho", "url"):
            if not d.get(c): falhas.append(f"{k}: sem campo {c}")
        if d.get("link") and not str(d["link"]).startswith("http"): falhas.append(f"{k}: link não é URL")
        pr = d.get("print")
        if pr:
            if pr.endswith("_semdestaque"): falhas.append(f"{k}: print sem realce ({pr})")
            arq = prints / f"{pr}.jpg"
            if not arq.exists(): falhas.append(f"{k}: print não existe ({arq.name})")
            side = prints / f"{pr}.jpg.txt"
            if side.exists() and d.get("trecho"):
                conferidas_trecho += 1
                # basta uma frase do trecho (separada por " · " ou ". ") estar no texto capturado
                # o trecho inteiro, ou qualquer pedaço dele com 6+ caracteres ("2T22 67,7%" tem 10 e vale)
                pedacos = [d["trecho"]] + [x for x in re.split(r" · |\. |; ", d["trecho"]) if len(x.strip()) >= 6]
                texto = norm(side.read_text())
                if not any(norm(x) in texto for x in pedacos):
                    falhas.append(f"{k}: nenhum pedaço do trecho está no texto capturado ({side.name})")
                # o número do claim tem que estar no texto capturado: senão o print prova outra frase
                nums = re.findall(r"\d[\d.,]*%?", d.get("claim", ""))
                sem = [n for n in nums if norm(n) not in texto and norm(n.replace(".", "")) not in texto.replace(".", "")]
                if nums and len(sem) == len(nums):
                    falhas.append(f"{k}: nenhum número do claim ({', '.join(nums)}) está no texto capturado")
        elif not d.get("nota"):
            falhas.append(f"{k}: sem print e sem nota explicando por quê")
    if not provas: falhas.append("ficha vazia: nenhuma prova para conferir")
    for f in falhas: print("  FAIL", f)
    print(f"\n  {len(provas)} fichas · {conferidas_trecho} trechos conferidos contra o texto capturado · {len(falhas)} FAIL")
    sys.exit(1 if falhas else 0)

if __name__ == "__main__":
    main()
