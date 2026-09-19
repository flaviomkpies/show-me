# -*- coding: utf-8 -*-
"""Print de PDF com o trecho realçado em amarelo, pelas coordenadas do texto .
A prova do show-me é VER o número na página da fonte; a página inteira espremida não prova nada.

Uso: python3 prova-print-pdf.py fonte.pdf 28 saida.jpg "0,7" "1,7" "13.857"
     (termo com ocorrência: "49%:2" pega a segunda ocorrência)

termo pode ser "texto" ou ("texto", n) para casar a n-ésima ocorrência (1-based).
O realce se adapta ao fundo: sobre fundo escuro vira contorno, para não sujar o número.
"""
import subprocess, pathlib
from PIL import Image, ImageDraw, ImageStat
from xml.etree import ElementTree as ET

NS = {"h": "http://www.w3.org/1999/xhtml"}

def caixas(pdf, pag):
    xml = subprocess.run(["pdftotext", "-bbox", "-f", str(pag), "-l", str(pag), pdf, "-"],
                         capture_output=True, text=True).stdout
    pagina = ET.fromstring(xml).find(".//h:page", NS)
    palavras = [(w.text or "", float(w.get("xMin")), float(w.get("yMin")),
                 float(w.get("xMax")), float(w.get("yMax")))
                for w in pagina.findall(".//h:word", NS)]
    return palavras, float(pagina.get("width")), float(pagina.get("height"))

def _casa(palavras, alvo):
    """Índices onde a sequência de palavras `alvo` começa."""
    for i in range(len(palavras) - len(alvo) + 1):
        if all(palavras[i + j][0].strip(".,;:").lower() == alvo[j].lower() for j in range(len(alvo))):
            yield i

def realca(pdf, pag, termos, destino, dpi=150, margem=6, largura=1280, contexto=230):
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(pag), "-l", str(pag), pdf, "/tmp/_pg"],
                   check=True, capture_output=True)
    png = sorted(pathlib.Path("/tmp").glob("_pg-*.png"))[-1]
    im = Image.open(png).convert("RGB")
    palavras, W, _ = caixas(pdf, pag)
    esc = im.width / W
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    faltou, caixas_px = [], []
    for termo in termos:
        texto, qual = termo if isinstance(termo, tuple) else (termo, 1)
        alvo = texto.split()
        inicios = list(_casa(palavras, alvo))
        if len(inicios) < qual:
            faltou.append(texto)
            continue
        i = inicios[qual - 1]
        x0 = min(palavras[i + j][1] for j in range(len(alvo))) * esc - margem
        y0 = min(palavras[i + j][2] for j in range(len(alvo))) * esc - margem
        x1 = max(palavras[i + j][3] for j in range(len(alvo))) * esc + margem
        y1 = max(palavras[i + j][4] for j in range(len(alvo))) * esc + margem
        recorte = im.crop((max(0, int(x0)), max(0, int(y0)), min(im.width, int(x1)), min(im.height, int(y1))))
        escuro = sum(ImageStat.Stat(recorte).mean[:3]) / 3 < 128
        fill = (255, 233, 77, 0) if escuro else (255, 233, 77, 120)
        d.rectangle([x0, y0, x1, y1], fill=fill, outline=(255, 214, 0, 255), width=4 if escuro else 3)
        caixas_px.append((x0, y0, x1, y1))
    im = Image.alpha_composite(im.convert("RGBA"), capa).convert("RGB")
    # recorte em volta dos realces: o print é o dado, não a página. Página inteira só se os realces
    # estiverem espalhados por mais de 60% da altura (aí o contexto é a página mesmo).
    if caixas_px:
        x0 = min(c[0] for c in caixas_px); y0 = min(c[1] for c in caixas_px)
        x1 = max(c[2] for c in caixas_px); y1 = max(c[3] for c in caixas_px)
        if (y1 - y0) < 0.6 * im.height:
            cy0 = max(0, int(y0 - contexto)); cy1 = min(im.height, int(y1 + contexto))
            im = im.crop((0, cy0, im.width, cy1))   # largura inteira: a frase em volta é o contexto
    if im.width > largura:
        im = im.resize((largura, int(im.height * largura / im.width)), Image.LANCZOS)
    im.save(destino, "JPEG", quality=80, optimize=True)
    png.unlink(missing_ok=True)
    # sidecar: o texto da página, para o gate conferir que o trecho da ficha está nela (nunca digitado)
    pathlib.Path(str(destino) + ".txt").write_text(
        subprocess.run(["pdftotext", "-layout", "-f", str(pag), "-l", str(pag), pdf, "-"], capture_output=True, text=True).stdout)
    return len(termos) - len(faltou), faltou, im.size

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 5: sys.exit(__doc__)
    pdf, pag, destino, termos = sys.argv[1], int(sys.argv[2]), sys.argv[3], []
    for t in sys.argv[4:]:
        termos.append((t.rsplit(":", 1)[0], int(t.rsplit(":", 1)[1])) if ":" in t and t.rsplit(":", 1)[1].isdigit() else t)
    n, faltou, size = realca(pdf, pag, termos, destino)
    print(f"{destino}: {n} realce(s), faltou {faltou}, {size[0]}x{size[1]}")
    sys.exit(1 if faltou else 0)
