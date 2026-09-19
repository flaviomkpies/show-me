#!/usr/bin/env python3
"""Acha um trecho ou numero num PDF e salva o print da pagina com o trecho destacado.

Uso:
    python3 highlight.py fonte.pdf --find "47%" "47 percent" "0.47" --out prova.jpg
    python3 highlight.py fonte.pdf --find "dynamic capabilities" --page 12 --ocr

Imprime a pagina (1-based) onde achou. Sai com 1 se nao achou: ai o caminho e OCR, ou capturar
a figura inteira e dizer que e captura, nao busca.

Atencao a paginacao: PDF de base de dados costuma ter capa, entao a pagina do arquivo nao e a
pagina impressa que voce vai citar. Confira uma vez por fonte e anote o deslocamento.
"""
import argparse
import io
import pathlib
import re
import sys

import fitz  # pymupdf


def variantes(termo):
    """Mesmo dado, grafias diferentes: 5,179 / 5179 / 5.179 ; 47% / 47 percent / 0.47."""
    v = {termo}
    n = re.fullmatch(r"([\d.,]+)\s*%?", termo.strip())
    if n:
        cru = n.group(1)
        digitos = re.sub(r"[.,]", "", cru)
        v |= {digitos, digitos + "%", digitos + " percent"}
        if len(digitos) > 3:
            v.add(digitos[:-3] + "," + digitos[-3:])
            v.add(digitos[:-3] + "." + digitos[-3:])
        if "%" in termo:
            try:
                v.add(str(round(float(cru.replace(",", ".")) / 100, 4)))
            except ValueError:
                pass
    return [x for x in v if x]


def achar(doc, termos, pagina=None):
    """Melhor pagina: a que tem mais ocorrencias. Match no inicio do documento (abstract,
    primeira figura) vence, porque menção solta no meio do texto prova menos."""
    paginas = [pagina - 1] if pagina else range(doc.page_count)
    melhor = None
    for i in paginas:
        if i < 0 or i >= doc.page_count:
            continue
        rects = []
        for t in termos:
            for var in variantes(t):
                rects += doc[i].search_for(var)
        if rects and (melhor is None or len(rects) > len(melhor[1])):
            melhor = (i, rects)
            if i < doc.page_count * 0.25:
                break
    return melhor


def por_ocr(doc, termos, out, dpi):
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print("--ocr pede: pip install pytesseract pillow (e o binario tesseract no sistema)",
              file=sys.stderr)
        return None
    alvos = [v.lower() for t in termos for v in variantes(t)]
    for i in range(doc.page_count):
        png = doc[i].get_pixmap(dpi=200).tobytes("png")
        txt = pytesseract.image_to_string(Image.open(io.BytesIO(png))).lower()
        if any(a in txt for a in alvos):
            doc[i].get_pixmap(dpi=dpi).save(out)
            return i
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--find", nargs="+", required=True)
    ap.add_argument("--out", default="prova.jpg")
    ap.add_argument("--page", type=int, help="1-based, quando voce ja sabe a pagina")
    ap.add_argument("--dpi", type=int, default=130, help="150 para pagina densa")
    ap.add_argument("--ocr", action="store_true", help="tenta OCR se nao achar no texto")
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    hit = achar(doc, a.find, a.page)

    if not hit and a.ocr:
        i = por_ocr(doc, a.find, a.out, a.dpi)
        if i is not None:
            print(f"{i + 1}  (por OCR, sem destaque: o texto esta dentro da imagem)")
            return 0

    if not hit:
        print(f"nao achei {a.find} em {pathlib.Path(a.pdf).name}. Tente --ocr, confira a "
              f"grafia, ou capture a figura inteira e diga que e captura.", file=sys.stderr)
        return 1

    i, rects = hit
    # guarde a pagina numa variavel: doc[i] devolve um objeto novo a cada acesso, e a annot
    # criada a partir de um descartado morre com ele ("annotation not bound to any page")
    page = doc[i]
    an = page.add_highlight_annot(rects)
    an.set_colors(stroke=(1, 0.92, 0))
    an.update()
    out = pathlib.Path(a.out)
    pix = page.get_pixmap(dpi=a.dpi)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        # JPEG q70: o caderno inteiro tem teto de 4 MB por arquivo entregue
        pix.pil_save(str(out), format="JPEG", quality=70)
    else:
        pix.save(str(out))
    print(i + 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
