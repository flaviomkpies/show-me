# -*- coding: utf-8 -*-
"""Print de página web com o trecho realçado em amarelo e recortado na região do dado .
Esconde anúncio, overlay e barra fixa; busca o termo só em p/li/td (o print do InfoMoney era o anúncio).

Uso: python3 prova-print-web.py alvos.json [saida_dir] [--headed]
     alvos: {"nome": {"url": "...", "termos": ["25,47", "nome da empresa"]}}
     --headed abre Chrome real (rodar sob `xvfb-run -a`): é o único jeito de passar Cloudflare/Turnstile.
     Reclame Aqui não passa nem assim: peça o print ao usuário."""
import io, json, pathlib, sys
from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright

D = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else pathlib.Path("provas_print")
D.mkdir(parents=True, exist_ok=True)
HEADED = "--headed" in sys.argv
ALVOS = json.loads(pathlib.Path(sys.argv[1]).read_text())
W, H = 1280, 620
VH = 980          # altura da janela: a captura sai dela, nunca da pagina inteira
ESCONDE = """() => {
  const css = document.createElement('style');
  css.textContent = `iframe,ins,[class*="publicidade"],[class*="advert"],[id*="advert"],[class*="banner"],
    [class*="-ad-"],[class*=" ad-"],[class*="ad_"],[id^="ad-"],[id*="-ad-"],[data-ad],[class*="newsletter"],
    [class*="fixed-top"],[class*="overlay"],[class*="modal"],[class*="backdrop"],[class*="paywall"],header,nav {display:none !important}
    body {overflow:visible !important}`;
  document.head.appendChild(css);
  // so barra/banner: elemento fixo GRANDE costuma ser o wrapper do conteudo (Wikipedia zerou
  // a pagina inteira assim, e o print saiu branco reportando sucesso)
  for (const el of document.querySelectorAll('body *')) {
    const st = getComputedStyle(el);
    if (st.position !== 'fixed' && st.position !== 'sticky') continue;
    if (/^(MARK|TABLE|THEAD|TBODY|TR|TD|TH|P|LI|ARTICLE|MAIN|SECTION|FIGURE)$/.test(el.tagName)) continue;
    const r = el.getBoundingClientRect();
    if (r.height > window.innerHeight * 0.6) continue;          // wrapper, nao barra
    if ((el.textContent || '').length > 400) continue;          // carrega conteudo
    el.style.setProperty('display', 'none', 'important');
  }
}"""
MARCA = """(termos) => {
  function envolve(no, termo) {
    var t = no.nodeValue, i = t.toLowerCase().indexOf(termo.toLowerCase());
    if (i < 0) return null;
    var meio = no.splitText(i); meio.splitText(termo.length);
    var m = document.createElement('mark'); m.className='__hl';
    m.style.cssText='background:#FFE94D !important;color:#111 !important;box-shadow:0 0 0 3px #FFE94D;border-radius:2px';
    meio.parentNode.replaceChild(m, meio); m.appendChild(meio); return m;
  }
  var achados = [];
  for (var k = 0; k < termos.length; k++) {
    var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: function (n) {
      if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      var p = n.parentElement; if (!p || /SCRIPT|STYLE|NOSCRIPT|MARK|TITLE/.test(p.tagName)) return NodeFilter.FILTER_REJECT;
      if (!p.closest('p,li,td')) return NodeFilter.FILTER_REJECT;
      var s = getComputedStyle(p); if (s.display==='none'||s.visibility==='hidden') return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT; } });
    var n, nos=[]; while ((n = w.nextNode())) nos.push(n);
    for (var j = 0; j < nos.length; j++) { var m = envolve(nos[j], termos[k]); if (m) { achados.push(m); break; } }
  }
  if (!achados.length) return null;
  // realce sem caixa (largura ou altura zero) nao aparece no print: vale como nao achado
  var caixas = achados.map(m => m.getBoundingClientRect()).filter(r => r.width > 0 && r.height > 0);
  if (!caixas.length) return null;
  var ys = caixas.map(r => r.top + window.scrollY);
  return { y0: Math.min.apply(null, ys), y1: Math.max.apply(null, ys), n: caixas.length };
}"""
res = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=not HEADED, args=["--disable-blink-features=AutomationControlled"] if HEADED else [])
    ctx = b.new_context(viewport={"width": W, "height": VH}, locale="pt-BR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    for nome, cfg in ALVOS.items():
        pg = ctx.new_page()
        try:
            pg.goto(cfg["url"] if cfg["url"].startswith("http") else "https://" + cfg["url"], wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)
            for t in ["Entendi","Aceitar","Aceito","Concordo","Fechar","Continuar"]:
                try:
                    bt = pg.get_by_role("button", name=t)
                    if bt.count(): bt.first.click(timeout=900); pg.wait_for_timeout(400); break
                except Exception: pass
            pg.evaluate(ESCONDE)
            pg.evaluate("()=>window.scrollTo(0,document.body.scrollHeight)"); pg.wait_for_timeout(1200)
            pg.evaluate("()=>window.scrollTo(0,0)"); pg.wait_for_timeout(400)
            hit = pg.evaluate(MARCA, cfg["termos"])
            if hit:
                # rolar ate o realce e fotografar a JANELA: print de pagina inteira em site longo
                # (Wikipedia: 66 mil px) leva minutos e estoura o tempo
                topo_vp = pg.evaluate("""() => {
                    const ms=[...document.querySelectorAll('mark.__hl')];
                    ms[0].scrollIntoView({block:'center'});
                    const r=ms[0].getBoundingClientRect();
                    return Math.max(0, Math.min(r.top - 130, window.innerHeight - 1));}""")
                pg.wait_for_timeout(400)
                alt = min(H, VH - int(topo_vp))
                img = pg.screenshot(clip={"x":0,"y":int(topo_vp),"width":W,"height":alt})
                res[nome] = f"destacado ({hit['n']}/{len(cfg['termos'])})"
                # sidecar: o parágrafo em volta do realce, para o gate conferir o trecho da ficha (nunca digitado)
                frase = pg.evaluate("() => [...document.querySelectorAll('mark.__hl')].map(m => { const c = m.closest('td,th') ? m.closest('tr') : m.closest('p,li,h1,h2,h3,h4,blockquote,figcaption,div'); return (c || m).innerText; }).join('\\n')")
                pathlib.Path(D / f"{nome}.jpg.txt").write_text(frase or "")  # nome == saida quando há destaque
            else:
                img = pg.screenshot(clip={"x":0,"y":0,"width":W,"height":min(H, VH)})
                res[nome] = "SEM DESTAQUE"   # o print sai com sufixo _semdestaque: não é prova, é diagnóstico
            im = Image.open(io.BytesIO(img)).convert("RGB")
            # print de cor única é página em branco: não é prova, mesmo com o termo "achado"
            if max(ImageStat.Stat(im).stddev) < 2:
                res[nome] = "SEM DESTAQUE (print em branco)"
            saida = nome if res[nome].startswith("destacado") else nome + "_semdestaque"
            im.save(D / f"{saida}.jpg", "JPEG", quality=78, optimize=True)
            res[nome] += f" · {im.size[0]}x{im.size[1]}"
        except Exception as e:
            res[nome] = "ERRO " + str(e)[:100]
        print(nome, "|", res[nome], flush=True); pg.close()
    b.close()
