"""Fluss über die Zeit - wie viele Lkw kommen in T Minuten am Gate an, und braucht man dafür das ganze Zeitnetz? - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Konzept - den zeitwiederholten Fluss von Ford und Fulkerson - und lässt stattdessen das Beispiel wachsen.
Fünfte Erweiterung (Stück 18, E5) der Netzwerkfluss-Linie der "Konzepte"-Reihe: Kind von Successive Shortest Paths (Kosten = Fahrzeit) und Dinic (Max-Flow im expandierten Netz). Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import zf_constants as C
import zf_dynamic as dyn
import zf_evaluation as ev
from zf_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from zf_visualization import build_arrivals, build_dist, build_map, build_ratio, build_sizes, build_value_curve

st.set_page_config(page_title="Fluss über die Zeit – Sebastian Hanisch", layout="wide")


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return "–" if x is None else f"{int(round(x)):,}".replace(",", " ")


def _pct(x, digits=1):
    return f"{100 * x:.{digits}f} %".replace(".", ",")


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params):
    return ev.analyse(ev.Params(*params))


@st.cache_resource(show_spinner=False, max_entries=32)
def _expanded(params):
    return ev.expanded(ev.Params(*params))


st.title("🚚 Fluss über die Zeit – wie viele Lkw kommen an?")
st.markdown(
    """
Ein Terminal will wissen: wie viele Lkw können in **T Minuten** am Gate ankommen, wenn jede Straße nur eine bestimmte Zahl Lkw **je Minute** einfahren lässt und jede Fahrt ihre **Zeit** dauert? Ein gewöhnlicher Max-Flow (Stück 1 bis 3) sieht die Zeit nicht:
er sagt nur, wie viele Lkw je Minute durchpassen, nicht, wie lange der erste braucht und wie viel eine lange Umleitung noch bringt, bevor die Frist abläuft.
Die naheliegende Antwort ist ein **Netz über die Zeit**: jede Kreuzung wird zu einem Knoten je Minute, jede Straße zu einer Kante von Minute k nach Minute k + Fahrzeit, und darauf rechnet man einen Max-Flow. Das ist exakt, aber das Netz wächst mit der Frist.
**Ford und Fulkerson (1958)** zeigten, dass man es nicht braucht: ein **einziger statischer Fluss** auf dem kleinen Straßennetz, bei dem die Fahrzeit als Kosten je Lkw zählt (Successive Shortest Paths aus Stück 4), in Wege zerlegt und in **jeder Minute wiederholt**, liefert genau den Wert des großen Netzes.
Diese Demo rechnet beides, vergleicht Größe und Aufwand - und zeigt die Grenze des Verfahrens: der Plan für eine Frist ist **für frühere Fristen nicht der beste**.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - fünfte Erweiterung (E5) der Netzwerkfluss-Linie der \"Konzepte\"-Reihe - **ein** Konzept an einem wachsenden Beispiel. "
    "Anders als in der Demo „Leercontainer-Repositionierung“ (Min-Cost-Flow im Zeit-Raum-Netz, Bestandsausgleich mit Vorschau-Fenster) geht es hier um den **größten Fluss innerhalb einer Frist** mit Kapazität je Minute und Fahrzeit je Straße, und um die Frage, ob man das Zeitnetz überhaupt aufbauen muss."
)

with st.expander("So funktioniert der zeitwiederholte Fluss", expanded=True):
    st.markdown(
        r"""
1. **Straße:** Kapazität $c_e$ (Lkw, die je Minute einfahren dürfen) und Fahrzeit $\tau_e$ (Minuten). Frist $T$: alle Lkw müssen bis Minute $T$ am Gate sein; die Einfahrt ist zu den Minuten $0,1,\dots$ möglich.
2. **Statischer Fluss:** ein Fluss $x$ mit $x_e\le c_e$, der die Summe der **Fahrzeiten** aller Lkw möglichst klein hält (Successive Shortest Paths: jede Runde füllt den zeitlich kürzesten Weg im Restgraphen auf, Rücknahmen sind erlaubt). Nur Wege mit Fahrzeit $\ell\le T$ zählen.
3. **Wege:** der Endfluss wird in Wege $P$ mit Menge $x_P$ und Fahrzeit $\ell_P$ zerlegt.
4. **Wiederholen:** jeder Weg fährt zu den Minuten $0,1,\dots,T-\ell_P$ mit der Menge $x_P$ los: $T-\ell_P+1$ Wiederholungen. Der Wert ist $V(T)=\sum_P x_P\,(T-\ell_P+1)$ und stimmt mit dem Max-Flow im zeitexpandierten Netz überein (Satz von Ford und Fulkerson).
5. **Alle Fristen zugleich:** die Rundenlängen hängen nicht von $T$ ab, ein Lauf liefert $V(T)$ für jede Frist. Die **schnellste Ankunft** von $N$ Lkw ist die kleinste Frist mit $V(T)\ge N$.
        """
    )

st.caption("🎯 Schnellstart – ein Beispiel laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox("Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
                           help="Ein zufälliges Straßennetz zum Gate oder ein festes Lehrnetz: zwei Straßen (schnell und eng gegen langsam und breit), ein Engpass mit Umweg, eine Kette und das Frühankunfts-Beispiel, in dem der Plan für eine späte Frist bei einer frühen Frist nichts liefert.")
    method = st.radio("Verfahren", list(C.METHODS), key="method_radio", format_func=lambda k: C.METHODS[k],
                      help="Successive Shortest Paths mit Rücknahmekanten liefert den besten Plan. „Nur Vorwärtskanten“ füllt kürzeste Wege, ohne je Fluss zurückzunehmen: eine Negativkontrolle, die in vielen Netzen unter dem Optimum bleibt.")
    deadline = st.slider("Frist T [Minuten]", *bounds("deadline_slider"), key="deadline_slider", help="Bis zu dieser Minute müssen die Lkw am Gate sein. Das expandierte Netz hat (T + 1) mal so viele Knoten wie das Straßennetz.")
    trucks = st.slider("Lkw für die schnellste Ankunft", *bounds("trucks_slider"), key="trucks_slider", step=10, help="Wie viele Lkw sollen ankommen? Gesucht ist die kleinste Frist, die dafür reicht.")
    if net_key == "roads":
        seed_widget("layers_slider")
        layers = st.slider("Schichten von Kreuzungen", *bounds("layers_slider"), key="layers_slider", help="Zwischen Sammelraum und Gate liegen so viele Schichten von Kreuzungen.")
        st.session_state[KEPT["layers_slider"]] = layers
        seed_widget("width_slider")
        width = st.slider("Kreuzungen je Schicht", *bounds("width_slider"), key="width_slider", help="Breite des Netzes: so viele Kreuzungen liegen nebeneinander in einer Schicht.")
        st.session_state[KEPT["width_slider"]] = width
        seed_widget("density_slider")
        density = st.slider("Dichte [%]", *bounds("density_slider"), key="density_slider", step=10, help="Anteil weiterer Straßen zwischen benachbarten Schichten (die Gerade gibt es immer); dazu Querstraßen mit halber Dichte.")
        st.session_state[KEPT["density_slider"]] = density
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed (neue Straßen, Kapazitäten und Fahrzeiten). Die Verteilungen über 40 feste Netze weiter unten ändern sich dabei nicht.")
    else:
        layers = int(st.session_state.get(KEPT["layers_slider"], C.DEFAULT_LAYERS))
        width = int(st.session_state.get(KEPT["width_slider"], C.DEFAULT_WIDTH))
        density = int(st.session_state.get(KEPT["density_slider"], C.DEFAULT_DENSITY))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Schichten, Breite, Dichte und Seed gehören zum Straßennetz.")

sync_query_params({"net_select": net_key, "method_radio": method, "deadline_slider": int(deadline), "trucks_slider": int(trucks), "layers_slider": int(layers), "width_slider": int(width), "density_slider": int(density), "seed_input": int(seed)})

# feste Lehrnetze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(layers), int(width), int(density), method, int(deadline), int(trucks), int(seed))
if net_key != "roads":
    params = (net_key, C.DEFAULT_LAYERS, C.DEFAULT_WIDTH, C.DEFAULT_DENSITY, method, int(deadline), int(trucks), C.DEFAULT_SEED)
with st.spinner("Rechne..."):
    a = _analysis(params)
net, plan, best, curve = a["net"], a["plan"], a["best"], a["curve"]
T = int(deadline)
label = net.kind != "roads"

# --- Lkw durchs Netz schicken -------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Lkw durchs Netz schicken, Minute für Minute")
if st.session_state.get("zf_step_owner") != params:
    st.session_state["zf_step"] = min(T, 5)
    st.session_state["zf_path"] = 0
    st.session_state["zf_step_owner"] = params
step_col, play_col = st.columns([5, 2])
with step_col:
    step = st.slider("Minute t", 0, T, key="zf_step", help="Zeitpunkt für die Karte: welche Straßen befahren zu dieser Minute wie viele Lkw je Minute (Einfahrtrate). Minute 0: alle Wege starten gleichzeitig.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch")
path_labels = ["kein Weg hervorgehoben"] + [f"Weg {i + 1}: {ev.path_label(net, p[0])} ({p[2]} je Minute, {p[3]} min)" for i, p in enumerate(plan.paths)]
path_choice = st.selectbox("Weg hervorheben", list(range(len(path_labels))), key="zf_path", format_func=lambda i: path_labels[i],
                           help="Der Plan besteht aus diesen Wegen; jeder Weg fährt zu den Minuten 0 bis T minus seiner Fahrzeit mit der angegebenen Menge los. Der gewählte Weg wird auf der Karte gestrichelt umrandet.")
view_slot = st.empty()
cum = a["cumulative"]


def _render(k):
    with view_slot.container():
        c1, c2 = st.columns([3, 2])
        load = dyn.load_at(net, plan.paths, T, k)
        hl = plan.paths[path_choice - 1][1] if path_choice > 0 else None
        c1.plotly_chart(build_map(net, load, label=label, highlight=hl), width="stretch", key=f"map_{k}")
        c2.plotly_chart(build_arrivals(cum, curve["curve"], T, t=k, height=460), width="stretch", key=f"arr_{k}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Am Gate bis Minute t", _int(cum[k]), help="Kumulierte Ankünfte unter dem Plan für die Frist T (grüne Linie).")
        m2.metric("Bis zur Frist T", _int(plan.value), help="Wert V(T) des Plans: Lkw, die bis zur Minute T ankommen.")
        m3.metric("Statischer Fluss f* [je Min.]", _int(curve["rate"]), help="Größter statischer Fluss (Stück 1 bis 3): so viele Lkw je Minute passen durchs Netz, ohne dass die Fahrzeit eine Rolle spielt.")
        m4.metric("Wege im Plan", _int(plan.n_paths), help="Wege der Zerlegung des statischen Flusses; jeder wird in jeder Minute wiederholt.")


if auto_play:
    for k in range(T + 1):
        _render(k)
        time.sleep(min(0.4, 6.0 / max(T, 1)))
    step = T
else:
    _render(step)
st.caption("Oben: Kantenbreite = Einfahrtrate zur Minute t, Farbe = Auslastung (Rate / Kapazität); blaues Quadrat = Sammelraum, rotes = Gate. Rechts die Ankünfte: der Plan für die Frist T (grün) gegen den jeweils besten Plan für jede frühere Frist (grau gestrichelt). "
           "Die Kurven fallen zusammen, wo der Plan auch für die frühere Frist optimal ist.")
if net_key == "early":
    st.markdown("**Frühankunft:** der beste Plan für Minute 3 schickt 5 Lkw je Minute über den kürzesten Weg S - A - B - T (3 Minuten). Für eine späte Frist ist es besser, diesen Weg zurückzunehmen; der Plan besteht dann aus S - A - T und S - B - T (je 4 Minuten) und liefert bis Minute 3 keinen einzigen Lkw.")
if method == "naive":
    st.warning(f"⚠️ Ohne Rücknahmekanten liefert der Plan {_int(plan.value)} Lkw, der beste Plan {_int(best.value)}: das Füllen kürzester Wege allein ist nicht optimal, weil ein einmal belegter Weg nie mehr freigegeben wird.")
else:
    st.success(f"✅ Bis Minute {T} können {_int(plan.value)} Lkw am Gate ankommen; der Plan besteht aus {plan.n_paths} Wegen ({plan.rate} Lkw je Minute) und braucht {_int(plan.scanned)} gescannte Kanten.")

st.markdown("---")

# --- Wie viel bringt Zeit? ---------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Wie viel bringt die Zeit?")
st.plotly_chart(build_value_curve(curve["curve"], curve["rate"], curve["shortest"], T), width="stretch", key="value_curve")
q1, q2, q3 = st.columns(3)
q1.metric("Fluss über die Zeit V(T)", _int(best.value), help="Bester Plan für die Frist T (Successive Shortest Paths).")
q2.metric("Statisch: f* mal T", _int(a["naive_bound"]), delta=f"{_pct(a['naive_bound'] / best.value - 1)} zu viel" if best.value else None, delta_color="off", help="Wer die Fahrzeit ignoriert und f* mit der Frist multipliziert, überschätzt die Lkw.")
q3.metric("Schranke f* (T − l + 1)", _int(a["static_bound"]), delta=f"{_pct(a['static_bound'] / best.value - 1)} zu viel" if best.value else None, delta_color="off", help="Selbst die Schranke, die den ersten Lkw erst nach der kürzesten Fahrzeit l ankommen lässt, ist zu hoch: die Straßen tragen ihre Höchstrate nur, wenn alle Wege gleichzeitig bis zum Ende offen sind.")
n_q, lower = a["quick"]
r1, r2, r3 = st.columns(3)
r1.metric(f"Schnellste Ankunft von {trucks} Lkw", "–" if n_q is None else f"{n_q} Minuten", help="Kleinste Frist T mit V(T) ≥ N.")
r2.metric("Untergrenze aus f*", "–" if lower is None else f"{lower} Minuten", help="ceil(N / f*) + kürzeste Fahrzeit − 1: schneller geht es auch ohne jeden Engpass nicht.")
r3.metric("Lücke", "–" if n_q is None else f"{n_q - lower} Minuten", help="Wie viel länger es wirklich dauert, weil nicht alle Wege von Anfang an frei sind und lange Umwege erst spät ankommen.")
st.caption("V(T) ist stückweise linear und wächst mit jeder neuen Straße, die sich noch lohnt (Knick). Die roten und orangen Linien sind statische Überschätzungen: sie kennen die Fahrzeit nicht (rot) oder nur die kürzeste (orange). Wo die grüne Linie steiler wird, kommt ein langsamerer, breiterer Weg dazu.")

st.markdown("---")

# --- Kompakt gegen expandiert ------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Kompakt statt expandiert")
with st.spinner("Baue das zeitexpandierte Netz und rechne Dinic..."):
    xp = _expanded(params)
st.markdown(f"Das Straßennetz hat **{xp['static_nodes']} Knoten und {xp['static_arcs']} Kanten**; das zeitexpandierte Netz für die Frist {xp['T']} **{_int(xp['nodes'])} Knoten und {_int(xp['arcs'])} Kanten**.")
x1, x2, x3 = st.columns(3)
x1.metric("Zeitwiederholter Fluss", _int(xp["value"]), help="Wert V(T) aus dem einen statischen Fluss.")
x2.metric("Max-Flow im Zeitnetz", _int(xp["expanded_value"]), help="Wert des maximalen Flusses im zeitexpandierten Netz (Dinic).")
x3.metric("Ohne Warte-Kanten", _int(xp["no_hold_value"]), help="Derselbe Max-Flow, aber ohne die Kanten, die Lkw an einer Kreuzung warten lassen: bei einer Ware und festen Kapazitäten hilft Warten nicht.")
if xp["equal"]:
    st.success(f"✅ Alle drei Werte sind gleich ({_int(xp['value'])}): das große Netz ist für diese Aufgabe nicht nötig.")
else:
    st.error("❌ Die Werte weichen ab - das dürfte nicht passieren.")
y1, y2 = st.columns(2)
y1.metric("Gescannte Kanten: zeitexpandiert (Dinic)", _int(xp["scanned"]), help="Aufwand des Max-Flow im großen Netz.")
y2.metric("Gescannte Kanten: zeitwiederholt", _int(xp["ssp_scanned"]), delta=f"{xp['scanned'] / xp['ssp_scanned']:.0f}-facher Aufwand".replace(".", ",") if xp["ssp_scanned"] else None, delta_color="off",
          help="Aufwand des statischen Verfahrens (Successive Shortest Paths) auf dem kleinen Netz; er hängt nicht von der Frist ab, sobald alle Wege einbezogen sind.")

st.markdown("---")

# --- Früher fertig? ----------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ist der Plan auch für frühere Fristen der beste?")
st.plotly_chart(build_ratio(a["early"], T), width="stretch", key="ratio_chart")
worst = min((r for r in a["early"] if r[3] is not None), key=lambda r: r[3], default=None)
if worst is None or worst[3] >= 0.9999:
    st.info("ℹ️ In diesem Netz ist der Plan für die Frist T auch für jede frühere Frist optimal: die Kurve liegt bei 100 %.")
else:
    st.warning(f"⚠️ Bei Frist {worst[0]} liefert der Plan für die Frist {T} nur {_int(worst[1])} Lkw statt {_int(worst[2])} ({_pct(worst[3], 0)}). Ein **Frühankunftsfluss** (Gale 1959) wäre für alle Fristen zugleich optimal; der zeitwiederholte Fluss ist es nicht, weil die Zerlegung des Endflusses andere Wege enthält als die frühen Runden.")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wie wächst der Aufwand mit der Frist?")
st.caption("Gescannte Kanten je Frist (Mittel über 5 feste Netze bei zufälligen Straßennetzen, sonst das gewählte Lehrnetz): Dinic auf dem zeitexpandierten Netz gegen Successive Shortest Paths auf dem Straßennetz.")
if st.button("Größe und Aufwand je Frist rechnen (dauert einige Sekunden)", key="sizes_start"):
    st.session_state["sizes_on"] = True
if st.session_state.get("sizes_on"):
    with st.spinner("Rechne Fristen von 5 bis 60 Minuten..."):
        rows = ev.sizes(ev.Params(*params))
    st.plotly_chart(build_sizes(rows), width="stretch", key="sizes_chart")
    st.table({"Frist [min]": [str(r["T"]) for r in rows], "Knoten im Zeitnetz / Straßennetz": [f"{_int(r['nodes'])} / {_int(r['static_nodes'])}" for r in rows]})
    st.table({"Frist [min]": [str(r["T"]) for r in rows], "Aufwand Dinic / zeitwiederholt": [f"{_int(r['dinic'])} / {_int(r['ssp'])}" for r in rows]})
    st.caption("Das Zeitnetz wächst linear mit der Frist, der Aufwand von Dinic darauf mit. Das statische Verfahren hängt nicht von der Frist ab, sobald alle Wege einbezogen sind (die Kurve wird flach).")

st.subheader("🔬 Gilt das in jedem Netz?")
st.caption(f"40 feste Netze mit den Einstellungen (Schichten, Breite, Dichte) und der Frist {T}: Gleichheit der Werte, Größe, Schranken, Frühankunft und die Negativkontrolle. Dazu die schnellste Ankunft von 50, 100 und 200 Lkw.")
if st.button("40 Netze durchrechnen (dauert etwa eine halbe Minute)", key="dist_start"):
    st.session_state["dist_on"] = True
if st.session_state.get("dist_on"):
    with st.spinner("Rechne 40 Netze..."):
        dist = ev.distribution(ev.Params(*params))
        qt = ev.quickest_table(ev.Params(*params))
    d1, d2, d3 = st.columns(3)
    d1.metric("Wert = Max-Flow im Zeitnetz", f"{dist['equal']} von {dist['n']}", help="Netze, in denen der zeitwiederholte Fluss genau den Wert des expandierten Netzes hat.")
    d2.metric("Ohne Warte-Kanten gleich", f"{dist['equal_no_hold']} von {dist['n']}")
    d3.metric("Zeitnetz: Knoten je Straßenknoten", _f(dist["node_ratio"], 1), help="Mittleres Verhältnis der Knotenzahlen: T + 1 Knoten je Kreuzung, dazu die zwei Verteiler.")
    e1, e2, e3 = st.columns(3)
    e1.metric("Aufwandsverhältnis Dinic / zeitwiederholt", f"{_f(dist['scan_ratio'], 0)}-fach")
    e2.metric("Statisch f* T gegen V(T)", f"+{_pct(dist['naive_bound'] - 1, 0)}", help="Mittlere Überschätzung, wenn man die Fahrzeit ignoriert.")
    e3.metric("Negativkontrolle unter dem Optimum", f"{dist['naive_lost']} von {dist['n']}", help=f"Netze, in denen „nur Vorwärtskanten“ weniger als das Optimum liefert; im Mittel {_pct(dist['naive_mean'], 1)} des Optimums, schlimmstenfalls {_pct(dist['naive_min'], 0)}.")
    st.plotly_chart(build_dist(dist), width="stretch", key="dist_chart")
    st.table({"Frühere Frist": [f"Minute {th}" for th in dist["thetas"]], "Netze mit Verlust": [f"{dist['early_share'][th][0]} von {dist['early_share'][th][1]}" for th in dist["thetas"]]})
    st.table({"Lkw": [str(r["n"]) for r in qt], "Schnellste Ankunft / Untergrenze [min]": [f"{_f(r['mean_T'], 1)} / {_f(r['mean_lower'], 1)}" for r in qt]})
    st.caption("Der Satz von Ford und Fulkerson gilt in jedem Netz; der Verlust bei früheren Fristen ist dagegen eine Eigenschaft der Netze: er ist bei sehr frühen Fristen groß und verschwindet nahe der Frist. Die schnellste Ankunft liegt im Mittel gut zwei Minuten über der Untergrenze aus dem statischen Fluss.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist - und wer ansetzt |
|---|---|
| **Eine Ware, ein Ziel** | Mehrere Güter oder Ziele machen das Problem schwer; der zeitwiederholte Fluss ist dann nicht mehr optimal. Für mehrere Quellen mit begrenztem Angebot (schnellste Verlegung, „quickest transshipment“) gibt es eigene Verfahren (Hoppe und Tardos), nicht gebaut. |
| **Kapazitäten und Fahrzeiten ändern sich nicht** | Bei zeitabhängigen Kapazitäten (Sperrungen, Schichtwechsel) hilft Warten, und die Wiederholung eines statischen Flusses reicht nicht mehr. Dann braucht man das Zeitnetz. |
| **Ganze Minuten** | Die Zeit ist in ganzen Minuten gerechnet (T − l + 1 Wiederholungen); im stetigen Modell ist es T − l. |
| **Frühankunft** | Ein Plan, der für jede Frist zugleich optimal ist (Gale 1959, für eine Senke), existiert, wird aber hier nicht gerechnet; die Demo misst nur, wie viel der Plan für eine Frist bei früheren Fristen verliert. |
| **Kein Warteraum am Gate** | Das Gate nimmt beliebig viele Lkw je Minute an; eine Terminalkapazität (Abfertigung je Minute, Warteschlange) ist eine andere Aufgabe (Demo „Lkw-Gate: Was bringt ein Terminsystem?“). |
| **Ein generiertes Netz** | Ein Schichtennetz mit erzeugten Kapazitäten und Fahrzeiten, kein reales Straßennetz und keine Fremddaten. |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: die zwölf Stücke der Hauptlinie, die Erweiterungen E1 (Projektauswahl, Graph Cuts, Gomory-Hu-Baum), E4 (Frank-Wolfe, Gradient Projection) und **E5: Fluss über die Zeit** (dieses Stück, gebaut).")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Fluss über die Zeit.** Netz $G=(V,E)$ mit Kapazität $c_e$ (Einfahrten je Zeiteinheit) und Fahrzeit $\tau_e\in\mathbb N$; Quelle $s$, Senke $t$, Frist $T$. Ein Fluss über die Zeit ist eine Funktion $f_e(\theta)\ge0$ mit $f_e(\theta)\le c_e$ für $\theta=0,\dots,T-\tau_e$ (Einfahrten), Flusserhaltung an jedem Knoten außer $s,t$
(mit Warten) und Ankunft bis Minute $T$; sein Wert ist die Zahl der bis $T$ in $t$ angekommenen Einheiten.

**Zeitexpandiertes Netz.** Knoten $(v,k)$ für $k=0,\dots,T$, Kanten $(u,k)\to(v,k+\tau_e)$ mit Kapazität $c_e$ und Warte-Kanten $(v,k)\to(v,k+1)$ ohne Grenze; ein Max-Flow von $\{(s,k)\}$ nach $\{(t,k)\}$ ist der Wert. Größe: $|V|(T+1)$ Knoten, $|E|(T+1)$ Kanten (gerundet).

**Zeitwiederholter Fluss** (Ford und Fulkerson 1958). Sei $x$ ein statischer Fluss mit $x_e\le c_e$ und $x=\sum_P x_P\chi_P$ eine Wegezerlegung, $\ell_P=\sum_{e\in P}\tau_e\le T$. Zu den Minuten $0,\dots,T-\ell_P$ fährt Weg $P$ mit Menge $x_P$ los. Der Wert
$$V(x)=\sum_P x_P\,(T-\ell_P+1)=(T+1)\,|x|-\sum_e\tau_e x_e.$$
Der Satz besagt: $\max_x V(x)$ (über statische Flüsse, deren Wege $\ell_P\le T$ haben) ist der Wert des größten Flusses über die Zeit. Der Ausdruck rechts ist ein Min-Cost-Flow mit Kosten $\tau_e$ und Preis $T+1$ je Einheit; die Successive-Shortest-Paths-Runden mit Weglänge $\ell\le T$ sind seine Lösung, und mit der Rundenmenge $x_r$ und der Rundenlänge $\ell_r$ ist $V(T)=\sum_{r:\ \ell_r\le T}x_r(T-\ell_r+1)$ für jedes $T$.

**Schranken.** $V(T)\le f^*\,(T-\ell_{\min}+1)$ mit dem größten statischen Fluss $f^*$ und der kürzesten Fahrzeit $\ell_{\min}$; die schnellste Ankunft von $N$ Einheiten braucht $T\ge\lceil N/f^*\rceil+\ell_{\min}-1$.

**Frühankunft.** $A_T(\theta)=\sum_P x_P\,(\theta-\ell_P+1)^+$ ist die Zahl der bis $\theta\le T$ angekommenen Einheiten des Plans für $T$; $A_T(\theta)\le V(\theta)$. Gleichheit für alle $\theta$ hieße Frühankunftsfluss (Gale 1959, Minieka, Wilkinson).

Implementiert in `zf_scenario.py` (Netz, Lehrnetze, Zufallsgenerator), `zf_ssp.py` und `zf_dinic.py` (Kopien aus ssp-demo und dinic-demo), `zf_dynamic.py` (Plan, Wegezerlegung, Kurven, Frühankunft), `zf_expanded.py` (zeitexpandiertes Netz), `zf_evaluation.py` (Vergleiche, Verteilungen).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Netzwerkfluss: vom Max-Flow zum Netzdesign](https://sebastianhanisch.net/konzepte-netzwerkfluss.html)."
)
