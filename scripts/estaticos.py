"""Gera o banner, os cards dos projetos e o README.md (a partir de scripts/README.modelo.md).

Cada card confere se o repositório é público: público ganha link e seta; privado mostra cadeado e fica sem link.
A automação roda isto todo dia, então mudar a visibilidade de um projeto no GitHub atualiza o perfil sozinho.
Rodar depois de mudar algum texto:  python scripts/estaticos.py
Os SVGs usam fontes do sistema de quem visita (sem baixar nada) e animações SMIL, que o GitHub exibe em <img>.
"""
import math
import os
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(RAIZ, "assets")
MODELO = os.path.join(RAIZ, "scripts", "README.modelo.md")

FUNDO, PAINEL, BORDA, GRADE = "#0B1422", "#0F1B2D", "#1E2D45", "#1A2738"
TEXTO, SUAVE, DESCR = "#E6EDF3", "#8B9BB0", "#A9B6C6"
TEAL, AMBAR = "#4FD1C5", "#E6B73C"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"
CHAR = 0.6  # largura de um caractere monoespaçado, em em (textLength garante o valor em qualquer fonte)

# --------------------------------------------------------------------------- textos
NOME = "Dionata Rafael Blauth"
SUBTITULO = "Software para laboratório de ensaios EMC"
FRASES = ["automação de ensaios EMC", "instrumentos via GPIB e SCPI",
          "visão computacional em ensaios", "apps desktop, mobile e web"]

PROJETOS = [
    # arquivo, título, etiqueta, descrição (2 linhas), tecnologias, ícone, repositório no GitHub
    ("halo", "HALO", "DESKTOP · EMC",
     ["Ensaios de emissão CISPR 15 e imunidade", "IEC 61000-4, controlando os instrumentos."],
     ["Python", "PySide6", "PyVISA", "SCPI"], "espectro", "rafablauth1/Halo"),
    ("vaia-ai", "Vaia Aí", "MOBILE · ANDROID",
     ["Futebol amador: grupos, times, placar ao", "vivo, ranking, financeiro e comunidade."],
     ["Expo", "React Native", "Supabase"], "campo", "rafablauth1/Chega-A-"),
    ("cispr15-labelo", "CISPR 15 LABELO", "DESKTOP · METROLOGIA",
     ["Relatórios de ensaio CISPR 15 e gestão", "metrológica: certificados e checagens."],
     ["Electron", "Next.js", "TypeScript"], "documento", "rafablauth1/CISPR-15_"),
    ("vigia-7s", "VIGIA-7S", "VISÃO COMPUTACIONAL",
     ["Leitura em tempo real de displays de 7", "segmentos durante ensaios EMC."],
     ["Python", "OpenCV", "ISO/IEC 17025"], "digito", "rafablauth1/vigia-7s"),
]


def publico(repo):
    """O GitHub responde 404 para repositório privado (ou inexistente) a quem não tem acesso."""
    req = urllib.request.Request(f"https://github.com/{repo}", method="HEAD", headers={"User-Agent": "perfil"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise  # outro erro (rede, limite): melhor falhar do que publicar um card errado


def salvar(nome, svg):
    caminho = os.path.join(ASSETS, nome)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print("gerado", os.path.relpath(caminho, RAIZ))


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------- banner
def _linha_do_tempo(janela, comprimentos):
    """Eventos (tempo, frase, caracteres visíveis) do texto digitando: digita, segura, apaga, próxima frase."""
    eventos = []
    for i, n in enumerate(comprimentos):
        t0 = i * janela
        digitar = min(1.5, n * 0.06)
        for k in range(1, n + 1):
            eventos.append((t0 + 0.15 + digitar * k / n, i, k))
        t_apaga = t0 + janela - 0.55
        for k in range(1, n + 1):
            eventos.append((t_apaga + 0.35 * k / n, i, n - k))
    return sorted(eventos)


def _animacao_discreta(atributo, pares, total, extra=""):
    """<animate> discreto (calcMode=discrete) que percorre os pares (tempo, valor) num ciclo de `total` segundos."""
    tempos = [0.0] + [t / total for t, _ in pares]
    valores = [pares[-1][1] if pares else 0] + [v for _, v in pares]
    tempos = [min(max(t, 0.0), 0.9999) for t in tempos]
    return (f'<animate attributeName="{atributo}" dur="{f(total)}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{";".join(f"{t:.4f}" for t in tempos)}" values="{";".join(f(v) for v in valores)}"{extra}/>')


def banner():
    W, H = 1200, 300
    # osciloscópio à direita
    gx0, gx1, gy0, gy1 = 730, 1150, 44, 256
    gw, gh = gx1 - gx0, gy1 - gy0
    grade = []
    for i in range(11):
        x = gx0 + gw * i / 10
        grade.append(f'<line x1="{f(x)}" y1="{gy0}" x2="{f(x)}" y2="{gy1}" class="g{" c" if i == 5 else ""}"/>')
    for j in range(7):
        y = gy0 + gh * j / 6
        grade.append(f'<line x1="{gx0}" y1="{f(y)}" x2="{gx1}" y2="{f(y)}" class="g{" c" if j == 3 else ""}"/>')

    # CH1: senoide (analógico) — desenhada com um período a mais e deslocada para dar a ilusão de sinal correndo
    lam, amp1, cy1 = 140, 30, gy0 + gh * 0.30
    pts = []
    x = gx0 - lam
    while x <= gx1 + lam:
        pts.append(f"{f(x)},{f(cy1 - amp1 * math.sin(2 * math.pi * (x - gx0) / lam))}")
        x += 3
    ch1 = f'<polyline points="{" ".join(pts)}" class="ch1"/>'
    # CH2: onda quadrada (digital)
    per, amp2, cy2 = 100, 20, gy0 + gh * 0.74
    d = []
    x = gx0 - per
    nivel = 1
    d.append(f"M{f(x)},{f(cy2 - amp2)}")
    while x < gx1 + per:
        y_atual = cy2 - amp2 * nivel
        x_prox = x + per / 2
        d.append(f"L{f(x_prox - 3)},{f(y_atual)}")
        nivel = -nivel
        d.append(f"L{f(x_prox + 3)},{f(cy2 - amp2 * nivel)}")
        x = x_prox
    ch2 = f'<path d="{" ".join(d)}" class="ch2"/>'

    # texto digitando
    fs = 21
    cw = fs * CHAR
    xl, yl = 62, 236
    prefixo = ">"
    xt = xl + 2 * cw  # o espaço depois do ">" é deslocamento (espaço no fim do texto o SVG descarta)
    janela = 3.6
    total = janela * len(FRASES)
    comps = [len(fr) for fr in FRASES]
    eventos = _linha_do_tempo(janela, comps)
    clips, frases = [], []
    for i, fr in enumerate(FRASES):
        pares = [(t, k * cw) for t, idx, k in eventos if idx == i]
        clips.append(f'<clipPath id="c{i}"><rect x="{f(xt)}" y="{yl - fs}" height="{fs + 8}" width="0">'
                     f'{_animacao_discreta("width", pares, total)}</rect></clipPath>')
        frases.append(f'<text x="{f(xt)}" y="{yl}" class="mono tl" textLength="{f(len(fr) * cw)}" '
                      f'lengthAdjust="spacingAndGlyphs" clip-path="url(#c{i})">{escape(fr)}</text>')
    pares_cursor = [(t, xt + k * cw) for t, _, k in eventos]
    cursor = (f'<rect x="{f(xt)}" y="{yl - fs + 3}" width="{f(cw * 0.9)}" height="{fs + 2}" fill="{AMBAR}">'
              f'{_animacao_discreta("x", pares_cursor, total)}'
              f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" '
              f'repeatCount="indefinite" calcMode="discrete"/></rect>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">{escape(NOME)}</title>
<desc id="d">{escape(SUBTITULO)}: {escape("; ".join(FRASES))}.</desc>
<defs>
  <linearGradient id="fundo" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{FUNDO}"/><stop offset="1" stop-color="#11233B"/>
  </linearGradient>
  <filter id="brilho" x="-20%" y="-50%" width="140%" height="200%">
    <feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="tela"><rect x="{gx0}" y="{gy0}" width="{gw}" height="{gh}" rx="6"/></clipPath>
  {"".join(clips)}
</defs>
<style>
  .sans {{ font-family: {SANS}; }}
  .mono {{ font-family: {MONO}; }}
  .g {{ stroke: {GRADE}; stroke-width: 1; }}
  .c {{ stroke: #26374F; stroke-dasharray: 3 4; }}
  .ch1 {{ fill: none; stroke: {TEAL}; stroke-width: 2.6; stroke-linejoin: round; }}
  .ch2 {{ fill: none; stroke: {AMBAR}; stroke-width: 2.4; stroke-linejoin: round; }}
  .tl {{ fill: {TEAL}; font-size: {fs}px; }}
</style>
<rect width="{W}" height="{H}" rx="18" fill="url(#fundo)"/>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{BORDA}"/>

<text x="{xl}" y="86" class="mono" font-size="18" fill="{SUAVE}">$ whoami</text>
<text x="{xl}" y="140" class="sans" font-size="44" font-weight="700" fill="{TEXTO}">{escape(NOME)}</text>
<text x="{xl}" y="180" class="sans" font-size="21" fill="{SUAVE}">{escape(SUBTITULO)}</text>
<text x="{xl}" y="{yl}" class="mono" font-size="{fs}" fill="{AMBAR}" textLength="{f(len(prefixo) * cw)}" lengthAdjust="spacingAndGlyphs">{escape(prefixo)}</text>
{"".join(frases)}
{cursor}

<rect x="{gx0}" y="{gy0}" width="{gw}" height="{gh}" rx="6" fill="#0A1220" stroke="{BORDA}"/>
<g clip-path="url(#tela)">
  {"".join(grade)}
  <g filter="url(#brilho)">
    <g>{ch1}<animateTransform attributeName="transform" type="translate" from="0 0" to="{-lam} 0" dur="2.8s" repeatCount="indefinite"/></g>
    <g>{ch2}<animateTransform attributeName="transform" type="translate" from="0 0" to="{-per} 0" dur="2.2s" repeatCount="indefinite"/></g>
  </g>
</g>
<text x="{gx0 + 10}" y="{gy0 + 20}" class="mono" font-size="12" fill="{TEAL}">CH1 · analógico</text>
<text x="{gx0 + 10}" y="{f(gy0 + gh * 0.52 + 6)}" class="mono" font-size="12" fill="{AMBAR}">CH2 · digital</text>
<text x="{gx1}" y="{gy1 + 22}" class="mono" font-size="11" fill="{SUAVE}" text-anchor="end">RUN · auto · 5 ms/div</text>
</svg>
'''
    salvar("banner.svg", svg)


# --------------------------------------------------------------------------- cards de projeto
def _icone(tipo, x, y):
    """Ícone de 48×48 desenhado com traços (sem fonte), dentro de um quadrado arredondado."""
    s = f'<rect x="{x}" y="{y}" width="52" height="52" rx="12" fill="#132238" stroke="#22344F"/>'
    t = f'stroke="{TEAL}" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    ox, oy = x + 10, y + 10
    if tipo == "espectro":  # traço com picos sempre abaixo da linha de limite (aprovado)
        tr = [(0, 30), (4, 29), (7, 14), (10, 28), (14, 27), (17, 19), (20, 28), (24, 27), (27, 21), (30, 29), (32, 30)]
        s += (f'<path d="M' + " L".join(f"{ox + a},{oy + b}" for a, b in tr) + f'" {t}/>'
              f'<path d="M{ox},{oy + 9} L{ox + 13},{oy + 9} L{ox + 13},{oy + 15} L{ox + 32},{oy + 15}" stroke="{AMBAR}" '
              f'stroke-width="2" stroke-dasharray="3 3" fill="none"/>')
    elif tipo == "campo":
        s += (f'<rect x="{ox}" y="{oy + 4}" width="32" height="24" rx="2" {t}/>'
              f'<line x1="{ox + 16}" y1="{oy + 4}" x2="{ox + 16}" y2="{oy + 28}" {t}/>'
              f'<circle cx="{ox + 16}" cy="{oy + 16}" r="5" {t}/>'
              f'<rect x="{ox}" y="{oy + 11}" width="5" height="10" {t}/>'
              f'<rect x="{ox + 27}" y="{oy + 11}" width="5" height="10" {t}/>')
    elif tipo == "documento":
        s += (f'<path d="M{ox + 6},{oy} L{ox + 22},{oy} L{ox + 30},{oy + 8} L{ox + 30},{oy + 32} L{ox + 6},{oy + 32} Z" {t}/>'
              f'<path d="M{ox + 22},{oy} L{ox + 22},{oy + 8} L{ox + 30},{oy + 8}" {t}/>'
              f'<path d="M{ox + 11},{oy + 20} L{ox + 16},{oy + 25} L{ox + 25},{oy + 14}" stroke="{AMBAR}" stroke-width="2.4" '
              f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    elif tipo == "digito":  # dígito "8" de 7 segmentos com o "7" aceso
        segs = {"a": (8, 2, 24, 2), "b": (26, 4, 26, 15), "c": (26, 19, 26, 30), "d": (8, 32, 24, 32),
                "e": (6, 19, 6, 30), "f": (6, 4, 6, 15), "g": (8, 17, 24, 17)}
        for k, (x1, y1, x2, y2) in segs.items():
            cor = AMBAR if k in "abc" else "#2B3A52"
            s += (f'<line x1="{ox + x1 + 1}" y1="{oy + y1}" x2="{ox + x2 + 1}" y2="{oy + y2}" stroke="{cor}" '
                  f'stroke-width="3.4" stroke-linecap="round"/>')
    return s


def _cadeado(x, y):
    return (f'<rect x="{x}" y="{y + 6}" width="12" height="9" rx="2" fill="{SUAVE}"/>'
            f'<path d="M{x + 2.5},{y + 6} V{y + 3.5} a3.5,3.5 0 0 1 7,0 V{y + 6}" stroke="{SUAVE}" stroke-width="1.8" fill="none"/>')


def _seta(x, y):
    return (f'<path d="M{x},{y + 14} L{x + 14},{y}" stroke="{AMBAR}" stroke-width="2.4" stroke-linecap="round"/>'
            f'<path d="M{x + 4},{y} L{x + 14},{y} L{x + 14},{y + 10}" stroke="{AMBAR}" stroke-width="2.4" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def card(arquivo, titulo, etiqueta, linhas, chips, icone, link):
    W, H = 600, 236
    partes = [f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{PAINEL}" stroke="{BORDA}"/>',
              _icone(icone, 28, 28),
              f'<text x="98" y="58" class="sans" font-size="25" font-weight="700" fill="{TEXTO}">{escape(titulo)}</text>',
              f'<text x="98" y="82" class="mono" font-size="12.5" fill="{TEAL}" letter-spacing="1">{escape(etiqueta)}</text>']
    if link:
        partes.append(_seta(W - 46, 30))
    else:
        partes.append(_cadeado(W - 92, 28))
        partes.append(f'<text x="{W - 74}" y="42" class="mono" font-size="12" fill="{SUAVE}">privado</text>')
    for i, linha in enumerate(linhas):
        partes.append(f'<text x="30" y="{128 + i * 26}" class="sans" font-size="17" fill="{DESCR}">{escape(linha)}</text>')
    x = 30
    for c in chips:
        larg = len(c) * 12.5 * CHAR + 22
        partes.append(f'<rect x="{f(x)}" y="182" width="{f(larg)}" height="28" rx="14" fill="#132238" stroke="#2A3B55"/>'
                      f'<text x="{f(x + 11)}" y="200.5" class="mono" font-size="12.5" fill="#C9D4E2" '
                      f'textLength="{f(len(c) * 12.5 * CHAR)}" lengthAdjust="spacingAndGlyphs">{escape(c)}</text>')
        x += larg + 10
    descricao = f"{titulo} — {' '.join(linhas)} Tecnologias: {', '.join(chips)}." + ("" if link else " Repositório privado.")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">{escape(descricao)}</title>
<style>.sans {{ font-family: {SANS}; }} .mono {{ font-family: {MONO}; }}</style>
{"".join(partes)}
</svg>
'''
    salvar(os.path.join("projetos", f"{arquivo}.svg"), svg)
    return descricao


# --------------------------------------------------------------------------- README
def readme():
    """README.md = modelo + cards (com link só para os repositórios públicos)."""
    imgs = []
    for arquivo, titulo, etiqueta, linhas, chips, icone, repo in PROJETOS:
        link = f"https://github.com/{repo}" if publico(repo) else None
        alt = card(arquivo, titulo, etiqueta, linhas, chips, icone, link).replace('"', "'")
        img = f'<img src="assets/projetos/{arquivo}.svg" width="49%" alt="{escape(alt)}">'
        imgs.append(f'  <a href="{link}">{img}</a>' if link else f"  {img}")
        print(f"  {titulo}: {'público, com link' if link else 'privado, sem link'}")
    bloco = '<p align="center">\n' + "\n".join(imgs) + "\n</p>"
    with open(MODELO, encoding="utf-8") as arq:
        modelo = arq.read()
    with open(os.path.join(RAIZ, "README.md"), "w", encoding="utf-8", newline="\n") as arq:
        arq.write(modelo.replace("<!-- PROJETOS -->", bloco))
    print("gerado README.md")


if __name__ == "__main__":
    banner()
    readme()
