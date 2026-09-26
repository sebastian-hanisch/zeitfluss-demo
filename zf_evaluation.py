"""Auswertung: der zeitwiederholte Fluss, die Gegenprobe im zeitexpandierten Netz, Größe und Aufwand, Schranken, schnellste Ankunft, Frühankunft und Verteilungen über feste Netze.
Alle Zufallsnetze kommen aus festen Seeds (zf_constants), unabhängig vom Nutzer-Seed."""

import statistics
from collections import namedtuple

import zf_constants as C
import zf_dynamic as dyn
import zf_expanded as ex
import zf_scenario as sc

Params = namedtuple("Params", "net layers width density method deadline trucks seed")
DEFAULT_PARAMS = Params(C.DEFAULT_NET, C.DEFAULT_LAYERS, C.DEFAULT_WIDTH, C.DEFAULT_DENSITY, C.DEFAULT_METHOD, C.DEFAULT_T, C.DEFAULT_TRUCKS, C.DEFAULT_SEED)


def network(params):
    return sc.build(params.net, params.layers, params.width, params.density, params.seed)


def thetas(T):
    """Die früheren Fristen, an denen die Frühankunft gemessen wird: ein Viertel, die Hälfte und drei Viertel der Frist."""
    return sorted({max(1, T // 4), max(1, T // 2), max(1, (3 * T) // 4)})


def analyse(params):
    """Plan für die Frist mit dem gewählten Verfahren, der beste Plan (Successive Shortest Paths), V(T) für alle Fristen, Schranken, schnellste Ankunft, Frühankunft."""
    net = network(params)
    T = params.deadline
    plan = dyn.plan(net, T, params.method)
    best = plan if params.method == "ssp" else dyn.plan(net, T, "ssp")
    curve = dyn.value_curve(net, C.T_MAX)
    naive_bound, static_bound = dyn.static_bounds(curve["rate"], curve["shortest"], T)
    quick = dyn.quickest(net, params.trucks)
    early = dyn.early_ratio(net, plan.paths, T)
    rate, cum = dyn.arrivals(plan.paths, T)
    return dict(net=net, plan=plan, best=best, curve=curve, naive_bound=naive_bound, static_bound=static_bound, quick=quick, early=early, arrival_rate=rate, cumulative=cum)


def expanded(params):
    """Gegenprobe im zeitexpandierten Netz für die Frist: Wert mit und ohne Warte-Kanten, Größe und Aufwand gegen das statische Netz."""
    net = network(params)
    T = params.deadline
    best = dyn.plan(net, T, "ssp")
    with_hold = ex.max_flow(net, T, True)
    no_hold = ex.max_flow(net, T, False)
    return dict(net=net, T=T, value=best.value, expanded_value=with_hold["value"], no_hold_value=no_hold["value"], nodes=with_hold["nodes"], arcs=with_hold["arcs"], scanned=with_hold["scanned"],
                ssp_scanned=best.scanned, static_nodes=net.n, static_arcs=net.m, equal=best.value == with_hold["value"] == no_hold["value"])


def sizes(params, Ts=C.SIZE_TS, seeds=C.SIZE_SEEDS):
    """Größe und Aufwand je Frist (Mittel über feste Netze bei zufälligen Straßennetzen, sonst das gewählte Lehrnetz): Knoten und Kanten des expandierten Netzes, gescannte Kanten von Dinic und vom statischen Verfahren."""
    nets = [network(params._replace(seed=s)) for s in seeds] if params.net == "roads" else [network(params)]
    rows = []
    for T in Ts:
        exs = [ex.max_flow(net, T) for net in nets]
        plans = [dyn.plan(net, T) for net in nets]
        rows.append(dict(T=T, nodes=statistics.fmean(e["nodes"] for e in exs), arcs=statistics.fmean(e["arcs"] for e in exs), dinic=statistics.fmean(e["scanned"] for e in exs),
                         ssp=statistics.fmean(p.scanned for p in plans), static_nodes=statistics.fmean(n.n for n in nets), static_arcs=statistics.fmean(n.m for n in nets)))
    return rows


def distribution(params, seeds=C.SWEEP_SEEDS):
    """Über feste Netze mit den Einstellungen und der gewählten Frist: Gleichheit mit dem expandierten Netz (mit und ohne Warte-Kanten), Größenverhältnis, Aufwandsverhältnis,
    Schranken, Frühankunft an ein Viertel, der Hälfte und drei Viertel der Frist, Verlust der Negativkontrolle."""
    T = params.deadline
    ths = thetas(T)
    rows = []
    for seed in seeds:
        net = network(params._replace(seed=seed, net="roads"))
        best = dyn.plan(net, T, "ssp")
        e = ex.max_flow(net, T, True)
        e0 = ex.max_flow(net, T, False)
        curve = dyn.value_curve(net, T)
        naive_bound, static_bound = dyn.static_bounds(curve["rate"], curve["shortest"], T)
        early = {th: r for th, _a, _b, r in dyn.early_ratio(net, best.paths, T, ths)}
        naive = dyn.plan(net, T, "naive")
        rows.append(dict(seed=seed, value=best.value, equal=best.value == e["value"], equal_no_hold=best.value == e0["value"], node_ratio=e["nodes"] / net.n, arc_ratio=e["arcs"] / net.m,
                         scan_ratio=e["scanned"] / best.scanned, naive_bound=(naive_bound / best.value) if best.value else None, static_bound=(static_bound / best.value) if best.value else None,
                         early=early, naive_value=naive.value))
    out = dict(n=len(rows), T=T, thetas=ths, rows=rows)
    out["equal"] = sum(1 for r in rows if r["equal"])
    out["equal_no_hold"] = sum(1 for r in rows if r["equal_no_hold"])
    out["node_ratio"] = statistics.fmean(r["node_ratio"] for r in rows)
    out["arc_ratio"] = statistics.fmean(r["arc_ratio"] for r in rows)
    out["scan_ratio"] = statistics.fmean(r["scan_ratio"] for r in rows)
    out["naive_bound"] = statistics.fmean(r["naive_bound"] for r in rows if r["naive_bound"] is not None)
    out["static_bound"] = statistics.fmean(r["static_bound"] for r in rows if r["static_bound"] is not None)
    out["early_mean"], out["early_min"], out["early_share"] = {}, {}, {}
    for th in ths:
        vals = [r["early"][th] for r in rows if r["early"].get(th) is not None]
        out["early_mean"][th] = statistics.fmean(vals) if vals else None          # None: in keinem Netz kann bis zu dieser Minute schon ein Lkw ankommen
        out["early_min"][th] = min(vals) if vals else None
        out["early_share"][th] = (sum(1 for v in vals if v < 0.9999), len(vals))
    lost = [r for r in rows if r["value"] and r["naive_value"] < r["value"]]
    out["naive_lost"] = len(lost)
    out["naive_mean"] = statistics.fmean(r["naive_value"] / r["value"] for r in rows if r["value"])
    out["naive_min"] = min(r["naive_value"] / r["value"] for r in rows if r["value"])
    return out


def quickest_table(params, ns=(50, 100, 200), seeds=C.SWEEP_SEEDS):
    """Schnellste Ankunft von n Lkw über feste Netze: Mittel der Frist T*, der Untergrenze ceil(n / f*) + l_min - 1 und der Lücke."""
    rows = []
    for n_trucks in ns:
        pairs = [dyn.quickest(network(params._replace(seed=s, net="roads")), n_trucks) for s in seeds]
        rows.append(dict(n=n_trucks, mean_T=statistics.fmean(p[0] for p in pairs), mean_lower=statistics.fmean(p[1] for p in pairs), mean_gap=statistics.fmean(p[0] - p[1] for p in pairs), equal=sum(1 for p in pairs if p[0] == p[1]), total=len(pairs)))
    return rows


def path_label(net, nodes):
    return " → ".join(net.labels[v] for v in nodes)
