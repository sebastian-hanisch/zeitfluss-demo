"""Plotly-Abbildungen: Straßenkarte mit der Einfahrtrate zur Minute t, Ankunftskurve, V(T) mit den statischen Schranken, Frühankunftsverhältnis, Größe und Aufwand, Verteilung.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Karten haben gleichen Maßstab (scaleanchor) mit automatischem Bereich; der Rand kommt über zwei unsichtbare Punkte
(ein fest vorgegebener Bereich wird beim ersten Zeichnen in schmaler Breite eingefroren). Beschriftungen von Kanten sind Annotationen mit heller Hinterlegung."""

from math import hypot

import plotly.graph_objects as go

import zf_constants as C

UTIL_BINS = ((0.0, 0.5, "Auslastung unter 50 %", "#2ca02c"), (0.5, 0.8, "50 bis 80 %", "#bcbd22"), (0.8, 1.0, "80 bis 100 %", "#ff7f0e"), (1.0, 1e9, "voll (100 %)", "#d62728"))


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.22), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _frame(fig, points, height, pad=8):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig.update_xaxes(visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False)
    fig.add_trace(go.Scatter(x=[min(xs) - pad, max(xs) + pad], y=[min(ys) - pad, max(ys) + pad], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    return _base(fig, height)


def _offsets(net):
    """Seitlicher Versatz je Kante: gegenläufige und parallele Kanten zwischen denselben Knoten liegen nebeneinander."""
    groups = {}
    for k, a in enumerate(net.arcs):
        groups.setdefault((min(a[0], a[1]), max(a[0], a[1])), []).append(k)
    off = {}
    for ks in groups.values():
        for i, k in enumerate(ks):
            off[k] = (i - (len(ks) - 1) / 2) * 5.0
    return off


def _segment(net, k, off):
    u, v = net.arcs[k][0], net.arcs[k][1]
    (x0, y0), (x1, y1) = net.pos[u], net.pos[v]
    length = hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = (y1 - y0) / length, -(x1 - x0) / length
    o = off[k]
    return x0 + nx * o, y0 + ny * o, x1 + nx * o, y1 + ny * o


def _bin(ratio):
    return 0 if ratio < 0.5 else 1 if ratio < 0.8 else 2 if ratio < 1.0 else 3


def _width(flow, top, lo=1.5, hi=9.0):
    return round(lo + (hi - lo) * flow / top) if top > 0 else lo


def build_map(net, load, height=460, label=False, highlight=None):
    """Straßenkarte: Kantenbreite ~ Einfahrtrate zur Minute t, Farbe = Auslastung (Rate / Kapazität); Sammelraum blau, Gate rot. `label`: Rate, Kapazität und Fahrzeit an die Kanten (kleine Lehrnetze).
    `highlight`: Netzkanten, die zusätzlich dunkel umrandet werden (ein gewählter Weg)."""
    fig = go.Figure()
    off = _offsets(net)
    top = max(max(load), max(a[2] for a in net.arcs)) if load else 1
    unused = [k for k in range(net.m) if load[k] <= 0]
    if unused:
        xs, ys = [], []
        for k in unused:
            x0, y0, x1, y1 = _segment(net, k, off)
            xs += [x0, x1, None]
            ys += [y0, y1, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="rgba(150,150,150,0.4)", width=1.5), hoverinfo="skip", name="keine Einfahrt"))
    used = [k for k in range(net.m) if load[k] > 0]
    for b, (_lo, _hi, name, color) in enumerate(UTIL_BINS):
        ks = [k for k in used if _bin(load[k] / net.arcs[k][2]) == b]
        by_width = {}
        for k in ks:
            by_width.setdefault(_width(load[k], top), []).append(k)
        first = True
        for w, group in sorted(by_width.items()):
            xs, ys = [], []
            for k in group:
                x0, y0, x1, y1 = _segment(net, k, off)
                xs += [x0, x1, None]
                ys += [y0, y1, None]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=w), hoverinfo="skip", name=name, showlegend=first))
            first = False
    hx, hy, ht = [], [], []
    for k in range(net.m):
        x0, y0, x1, y1 = _segment(net, k, off)
        hx.append((x0 + x1) / 2)
        hy.append((y0 + y1) / 2)
        u, v, c, tau, _kind = net.arcs[k]
        ht.append(f"{net.names[u]} → {net.names[v]}: Einfahrt {load[k]} von {c} Lkw je Minute, Fahrzeit {tau} Minuten")
    fig.add_trace(go.Scatter(x=hx, y=hy, mode="markers", marker=dict(size=9, opacity=0), hovertext=ht, hoverinfo="text", showlegend=False))
    if highlight:
        xs, ys = [], []
        for k in highlight:
            x0, y0, x1, y1 = _segment(net, k, off)
            xs += [x0, x1, None]
            ys += [y0, y1, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#111", width=2, dash="dot"), hoverinfo="skip", name="gewählter Weg"))
    if label:
        for k in range(net.m):
            x0, y0, x1, y1 = _segment(net, k, off)
            u, v, c, tau, _kind = net.arcs[k]
            fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=f"{load[k]}/{c} · {tau} min", showarrow=False, font=dict(size=10), bgcolor="rgba(255,255,255,0.85)", borderpad=1)
    others = [v for v in range(net.n) if v not in (net.s, net.t)]
    if others:
        fig.add_trace(go.Scatter(x=[net.pos[v][0] for v in others], y=[net.pos[v][1] for v in others], mode="markers+text" if label else "markers", text=[net.labels[v] for v in others] if label else None, textposition="top center",
                                 textfont=dict(size=10), marker=dict(size=7, color=C.COLORS["node"]), hovertext=[net.names[v] for v in others], hoverinfo="text", showlegend=False))
    fig.add_trace(go.Scatter(x=[net.pos[net.s][0]], y=[net.pos[net.s][1]], mode="markers+text", text=["S"], textposition="middle right", marker=dict(size=15, symbol="square", color=C.COLORS["source"], line=dict(width=1.5, color="#333")),
                             hovertext=[net.names[net.s]], hoverinfo="text", name="Sammelraum"))
    fig.add_trace(go.Scatter(x=[net.pos[net.t][0]], y=[net.pos[net.t][1]], mode="markers+text", text=["T"], textposition="middle right", marker=dict(size=15, symbol="square", color=C.COLORS["gate"], line=dict(width=1.5, color="#333")),
                             hovertext=[net.names[net.t]], hoverinfo="text", name="Gate"))
    return _frame(fig, net.pos, height)


def build_arrivals(cumulative, best_curve, T, t=None, height=340):
    """Kumulierte Ankünfte je Minute unter dem Plan für die Frist T (grün) gegen den dort jeweils besten Plan (grau gestrichelt: V(theta) für jede frühere Frist)."""
    fig = go.Figure()
    xs = list(range(T + 1))
    fig.add_trace(go.Scatter(x=xs, y=best_curve[:T + 1], mode="lines", name="bester Plan für jede Frist", line=dict(color=C.COLORS["best"], width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=xs, y=cumulative, mode="lines", name="Plan für die Frist T", line=dict(color=C.COLORS["plan"], width=3)))
    if t is not None:
        fig.add_vline(x=t, line=dict(color="#111", dash="dash"), annotation_text="Bild", annotation_position="top")
    fig.update_xaxes(title="Minute (Frist)")
    fig.update_yaxes(title="Lkw am Gate (kumuliert)")
    return _base(fig, height)


def build_value_curve(curve, rate, shortest, T, t_max=None, height=340):
    """V(T) gegen die statischen Schranken f* T (ignoriert die Fahrzeit) und f* (T - l_min + 1); senkrecht die gewählte Frist."""
    t_max = t_max or len(curve) - 1
    xs = list(range(t_max + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[rate * x for x in xs], mode="lines", name="statisch: f* mal Frist", line=dict(color=C.COLORS["static"], width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=xs, y=[max(0, rate * (x - shortest + 1)) if shortest is not None else 0 for x in xs], mode="lines", name="Schranke: f* (Frist - kürzeste Fahrzeit + 1)", line=dict(color=C.COLORS["bound"], width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=xs, y=curve[:t_max + 1], mode="lines", name="V(T): Fluss über die Zeit", line=dict(color=C.COLORS["plan"], width=3)))
    fig.add_vline(x=T, line=dict(color="#111", dash="dash"), annotation_text="Frist", annotation_position="top")
    fig.update_xaxes(title="Frist T [Minuten]")
    fig.update_yaxes(title="Lkw bis zur Frist")
    return _base(fig, height)


def build_ratio(early, T, height=280):
    """Verhältnis A_T(theta) / V(theta): wie viel der Plan für die Frist T bei früheren Fristen gegenüber dem dort besten Plan liefert (Minuten ohne möglichen Lkw ausgelassen)."""
    pts = [(th, r) for th, _a, _b, r in early if r is not None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines+markers", name="Plan für die Frist T gegen den besten", line=dict(color=C.COLORS["plan"], width=2)))
    fig.add_hline(y=1.0, line=dict(color="rgba(80,80,80,0.5)", dash="dot", width=1))
    fig.update_xaxes(title="frühere Frist theta [Minuten]", range=[0, T + 1])
    fig.update_yaxes(title="Anteil des besten Plans", range=[0, 1.08], tickformat=".0%")
    return _base(fig, height)


def build_sizes(rows, height=320):
    """Aufwand in gescannten Kanten gegen die Frist (logarithmisch): Dinic auf dem zeitexpandierten Netz gegen Successive Shortest Paths auf dem Straßennetz."""
    fig = go.Figure()
    xs = [r["T"] for r in rows]
    fig.add_trace(go.Scatter(x=xs, y=[r["dinic"] for r in rows], mode="lines+markers", name="zeitexpandiertes Netz (Dinic)", line=dict(color=C.COLORS["dinic"], width=2)))
    fig.add_trace(go.Scatter(x=xs, y=[r["ssp"] for r in rows], mode="lines+markers", name="Straßennetz (zeitwiederholter Fluss)", line=dict(color=C.COLORS["ssp"], width=2)))
    fig.update_xaxes(title="Frist T [Minuten]")
    fig.update_yaxes(title="gescannte Kanten", type="log")
    return _base(fig, height)


def build_dist(dist, height=300):
    """Frühankunft über die festen Netze: Mittel und schlechtester Wert von A_T(theta) / V(theta) an den früheren Fristen."""
    ths = [th for th in dist["thetas"] if dist["early_mean"][th] is not None]
    x = [f"Minute {th}" for th in ths]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[dist["early_mean"][th] for th in ths], name="Mittel", marker_color="#2ca02c"))
    fig.add_trace(go.Bar(x=x, y=[dist["early_min"][th] for th in ths], name="schlechtestes Netz", marker_color="#d62728"))
    fig.update_yaxes(title="Anteil des besten Plans", range=[0, 1.08], tickformat=".0%")
    fig.update_layout(barmode="group")
    return _base(fig, height)
