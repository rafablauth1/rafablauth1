"""Desenha assets/atividade.svg: as contribuições do último ano como a tela de um analisador de espectro.

Na automação do GitHub usa a API GraphQL (variável GITHUB_TOKEN). Sem token, lê a página pública de contribuições.
Rodar localmente:  python scripts/atividade.py
"""
import datetime as dt
import json
import math
import os
import re
import urllib.request
from xml.sax.saxutils import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "assets", "atividade.svg")
USUARIO = os.environ.get("USUARIO") or "rafablauth1"

PAINEL, BORDA, GRADE, TELA = "#0F1B2D", "#1E2D45", "#1A2738", "#0A1220"
TEXTO, SUAVE = "#E6EDF3", "#8B9BB0"
TEAL, AMBAR = "#4FD1C5", "#E6B73C"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MESES_LONGOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
                "novembro", "dezembro"]


# --------------------------------------------------------------------------- dados
def _pedir(url, dados=None, cab=None):
    req = urllib.request.Request(url, data=dados, headers={"User-Agent": f"perfil-{USUARIO}", **(cab or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def dias_graphql(token):
    consulta = ("query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{"
                "weeks{contributionDays{date contributionCount}}}}}}")
    corpo = json.dumps({"query": consulta, "variables": {"login": USUARIO}}).encode()
    resp = json.loads(_pedir("https://api.github.com/graphql", corpo,
                             {"Authorization": f"bearer {token}", "Content-Type": "application/json"}))
    if resp.get("errors"):
        raise RuntimeError(resp["errors"])
    semanas = resp["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return sorted((d["date"], d["contributionCount"]) for s in semanas for d in s["contributionDays"])


def dias_pagina():
    """Página pública do calendário: cada <td> tem data-date e id; a dica <tool-tip for=id> traz a contagem."""
    html = _pedir(f"https://github.com/users/{USUARIO}/contributions").decode("utf-8")
    datas = {}
    for td in re.findall(r"<td\b[^>]*ContributionCalendar-day[^>]*>", html):
        d, i = re.search(r'data-date="([\d-]+)"', td), re.search(r'\bid="([^"]+)"', td)
        if d and i:
            datas[i.group(1)] = d.group(1)
    dias = {}
    for alvo, texto in re.findall(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        if alvo in datas:
            n = re.match(r"\s*([\d,]+)", texto)
            dias[datas[alvo]] = int(n.group(1).replace(",", "")) if n else 0
    if not dias:
        raise RuntimeError("formato da página de contribuições mudou")
    return sorted(dias.items())


# --------------------------------------------------------------------------- desenho
def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def br(v, casas=1):
    return f"{v:.{casas}f}".replace(".", ",")


def desenhar(dias):
    W, H = 1200, 440
    px0, px1, py0, py1 = 78, 1150, 104, 320
    datas = [dt.date.fromisoformat(d) for d, _ in dias]
    vals = [c for _, c in dias]
    # conta com menos de um ano: o gráfico começa no mês da 1ª contribuição (sem meses vazios antes dela)
    primeiro = next((i for i, v in enumerate(vals) if v), None)
    if primeiro is not None:
        inicio = datas[primeiro].replace(day=1)
        corte = next(i for i, d in enumerate(datas) if d >= inicio)
        datas, vals = datas[corte:], vals[corte:]
    n = len(vals)
    meses_span = max(1, round(n / 30.44))
    periodo = ("últimos 12 meses" if meses_span >= 12
               else f"desde {MESES[datas[0].month - 1]} {datas[0].year}" if datas else "")
    total, ativos, maxv = sum(vals), sum(1 for v in vals if v), max(vals) if vals else 0
    teto = math.log10(1 + max(maxv, 1))

    def X(i):
        return px0 + (px1 - px0) * i / max(n - 1, 1)

    def Y(v):  # escala logarítmica, como num analisador: picos grandes não esmagam os pequenos
        return py1 - (py1 - py0) * 0.82 * math.log10(1 + v) / teto

    partes = []
    # grade: um traço por início de mês, e níveis de 1, 3, 10, 30, 100… contribuições por dia
    for i, d in enumerate(datas):
        if d.day == 1:
            x = X(i)
            partes.append(f'<line x1="{f(x)}" y1="{py0}" x2="{f(x)}" y2="{py1}" class="g"/>')
            rot = MESES[d.month - 1] + (f" {d.year % 100:02d}" if d.month == 1 else "")
            partes.append(f'<text x="{f(x)}" y="{py1 + 20}" class="mono eixo" text-anchor="middle">{rot}</text>')
    nivel = 1
    while nivel <= maxv * 1.05 or nivel == 1:
        y = Y(nivel)
        partes.append(f'<line x1="{px0}" y1="{f(y)}" x2="{px1}" y2="{f(y)}" class="g"/>')
        partes.append(f'<text x="{px0 - 10}" y="{f(y + 4)}" class="mono eixo" text-anchor="end">{nivel}</text>')
        nivel = nivel * 3 if str(nivel).startswith("1") else nivel * 10 // 3
    partes.append(f'<line x1="{px0}" y1="{py1}" x2="{px1}" y2="{py1}" class="g base"/>')

    # traço e área
    pts = " ".join(f"{f(X(i))},{f(Y(v))}" for i, v in enumerate(vals))
    area = f"M{px0},{py1} L" + pts.replace(" ", " L") + f" L{px1},{py1} Z"
    partes.append(f'<path d="{area}" fill="url(#area)" class="area"/>')
    partes.append(f'<polyline points="{pts}" class="traco" pathLength="1000"/>')

    # média por dia ativo (linha tracejada, como uma linha de limite)
    if ativos:
        media = total / ativos
        ym = Y(media)
        partes.append(f'<line x1="{px0}" y1="{f(ym)}" x2="{px1}" y2="{f(ym)}" class="media"/>')
        partes.append(f'<text x="{px0 + 10}" y="{f(ym - 8)}" class="mono rot-media">'
                      f'média por dia ativo · {br(media)}</text>')

    # marcadores dos 3 maiores picos: só o número sobre o pico; os valores vão na tabela do cabeçalho
    picos = sorted(range(n), key=lambda i: (-vals[i], -i))[:3]
    picos = [i for i in picos if vals[i] > 0]
    tabela = []
    for k, i in enumerate(picos, 1):
        x, y = X(i), Y(vals[i])
        partes.append(f'<g class="marc"><path d="M{f(x - 5.5)},{f(y - 10)} L{f(x + 5.5)},{f(y - 10)} L{f(x)},{f(y - 3)} Z" '
                      f'fill="{AMBAR}"/><text x="{f(x)}" y="{f(y - 15)}" class="mono num-marc" text-anchor="middle">{k}</text></g>')
        tabela.append(f"M{k} {vals[i]} · {datas[i]:%d/%m}")
    x = px1  # tabela de marcadores no cabeçalho, da direita para a esquerda (M1 fica à esquerda)
    for item in reversed(tabela):
        larg = len(item) * 12 * 0.6
        partes.append(f'<text x="{f(x)}" y="70" class="mono rot-tab marc" text-anchor="end" textLength="{f(larg)}" '
                      f'lengthAdjust="spacingAndGlyphs">{escape(item)}</text>')
        x -= larg + 26

    # leituras (como no rodapé do analisador)
    i_max = picos[0] if picos else 0
    por_mes = {}
    for d, v in zip(datas, vals):
        por_mes[(d.year, d.month)] = por_mes.get((d.year, d.month), 0) + v
    (ano_m, mes_m), soma_m = max(por_mes.items(), key=lambda kv: (kv[1], kv[0])) if por_mes else ((0, 1), 0)
    leituras = [("TOTAL", f"{total}"), ("DIAS ATIVOS", f"{ativos}"),
                ("PICO", f"{maxv} em {datas[i_max]:%d/%m}" if maxv else "—"),
                ("MÊS MAIS ATIVO", f"{MESES_LONGOS[mes_m - 1]} · {soma_m}" if soma_m else "—")]
    larg_bloco = (px1 - px0) / len(leituras)
    for j, (rot, val) in enumerate(leituras):
        x = px0 + j * larg_bloco
        partes.append(f'<rect x="{f(x + 4)}" y="352" width="{f(larg_bloco - 8)}" height="58" rx="8" fill="{TELA}" '
                      f'stroke="{BORDA}"/>'
                      f'<text x="{f(x + 20)}" y="374" class="mono rot-leit">{escape(rot)}</text>'
                      f'<text x="{f(x + 20)}" y="399" class="mono val-leit">{escape(val)}</text>')

    ultimo = datas[-1] if datas else dt.date.today()
    titulo = (f"Atividade no GitHub ({periodo}): {total} contribuições em {ativos} dias; "
              f"pico de {maxv} em {datas[i_max]:%d/%m/%Y}." if vals else "Atividade no GitHub")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">{escape(titulo)}</title>
<defs>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{TEAL}" stop-opacity=".32"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="feixe" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{TEAL}" stop-opacity="0"/><stop offset="1" stop-color="{TEAL}" stop-opacity=".22"/>
  </linearGradient>
  <filter id="brilho" x="-5%" y="-20%" width="110%" height="140%">
    <feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="tela"><rect x="{px0}" y="{py0 - 30}" width="{px1 - px0}" height="{py1 - py0 + 30}"/></clipPath>
</defs>
<style>
  .sans {{ font-family: {SANS}; }}
  .mono {{ font-family: {MONO}; }}
  .g {{ stroke: {GRADE}; stroke-width: 1; }}
  .base {{ stroke: #2A3B55; }}
  .eixo {{ font-size: 11.5px; fill: {SUAVE}; }}
  .traco {{ fill: none; stroke: {TEAL}; stroke-width: 1.8; stroke-linejoin: round; filter: url(#brilho);
            stroke-dasharray: 1000; stroke-dashoffset: 1000; animation: desenhar 2.6s ease-out .2s forwards; }}
  .area {{ opacity: 0; animation: aparecer 1.2s ease-out 1.6s forwards; }}
  .marc {{ opacity: 0; animation: aparecer .6s ease-out 2.6s forwards; }}
  .media {{ stroke: {AMBAR}; stroke-width: 1.4; stroke-dasharray: 6 5; opacity: .85; }}
  .rot-media {{ font-size: 12px; fill: {AMBAR}; }}
  .num-marc {{ font-size: 11px; fill: {AMBAR}; font-weight: 700; }}
  .rot-tab {{ font-size: 12px; fill: {AMBAR}; }}
  .rot-leit {{ font-size: 11px; fill: {SUAVE}; letter-spacing: 1px; }}
  .val-leit {{ font-size: 19px; fill: {TEXTO}; }}
  .feixe {{ animation: varrer 7s linear 3s infinite; opacity: 0; }}
  @keyframes desenhar {{ to {{ stroke-dashoffset: 0; }} }}
  @keyframes aparecer {{ to {{ opacity: 1; }} }}
  @keyframes varrer {{ 0% {{ transform: translateX(0); opacity: 1; }} 100% {{ transform: translateX({px1 - px0 - 60}px); opacity: 1; }} }}
  @media (prefers-reduced-motion: reduce) {{
    .traco {{ animation: none; stroke-dashoffset: 0; }} .area, .marc {{ animation: none; opacity: 1; }} .feixe {{ display: none; }}
  }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{PAINEL}" stroke="{BORDA}"/>
<text x="32" y="46" class="sans" font-size="22" font-weight="700" fill="{TEXTO}">Espectro de contribuições</text>
<text x="32" y="70" class="mono" font-size="12.5" fill="{SUAVE}">contribuições por dia · {escape(periodo)}</text>
<text x="{px1}" y="46" class="mono" font-size="12" fill="{SUAVE}" text-anchor="end">SPAN {min(meses_span, 12)} meses · RBW 1 dia · escala log</text>
<rect x="{px0}" y="{py0 - 30}" width="{px1 - px0}" height="{py1 - py0 + 30}" fill="{TELA}" rx="4"/>
<g clip-path="url(#tela)"><rect x="{px0}" y="{py0 - 30}" width="60" height="{py1 - py0 + 30}" fill="url(#feixe)" class="feixe"/></g>
{"".join(partes)}
<text x="{W - 32}" y="{H - 10}" class="mono" font-size="10.5" fill="#5B6B80" text-anchor="end">atualizado em {ultimo:%d/%m/%Y}</text>
</svg>
'''


def main():
    token = os.environ.get("GITHUB_TOKEN")
    dias = dias_graphql(token) if token else dias_pagina()
    hoje = dt.date.today().isoformat()
    dias = [d for d in dias if d[0] <= hoje]
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as arq:
        arq.write(desenhar(dias))
    print(f"gerado {os.path.relpath(SAIDA, RAIZ)}: {len(dias)} dias, {sum(v for _, v in dias)} contribuições")


if __name__ == "__main__":
    main()
