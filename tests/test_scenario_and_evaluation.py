"""Szenario (Schichtennetz, Lehrnetze, Zufallsstrom) und Auswertung (Analyse, Gegenprobe, Größe, Verteilung, schnellste Ankunft)."""

import pytest

import zf_constants as C
import zf_evaluation as ev
import zf_scenario as sc

P = ev.DEFAULT_PARAMS


def test_generation_is_deterministic_and_seed_dependent():
    a, b, c = sc.generate(3, 4, 60, 5), sc.generate(3, 4, 60, 5), sc.generate(3, 4, 60, 6)
    assert a == b and a != c


def test_grid_structure_and_ranges():
    """3 Schichten mit je 4 Kreuzungen: 14 Knoten; Kapazität und Fahrzeit in den Grenzen; jede Straße führt von einer Schicht in dieselbe oder die nächste."""
    n = sc.generate(3, 4, 60, 1)
    assert (n.n, n.m, n.s, n.t) == (14, 34, 0, 1)
    assert all(1 <= c <= 8 and 1 <= k <= 5 for _u, _v, c, k, _a in n.arcs)
    layer = lambda v: -1 if v == 0 else 99 if v == 1 else (v - 2) // 4
    assert all(layer(v) - layer(u) in (0, 1) or u == 0 or v == 1 for u, v, *_r in n.arcs)


def test_density_changes_only_which_roads_exist():
    """Die Zufallszahlen werden für jede mögliche Straße gezogen: bei höherer Dichte kommen Straßen dazu, keine verschwindet oder ändert ihre Werte."""
    thin, thick = set(sc.generate(3, 4, 30, 9).arcs), set(sc.generate(3, 4, 100, 9).arcs)
    assert thin < thick


def test_lessons_and_build_dispatch():
    assert set(sc.LESSONS) == set(C.FIXED_NETS) and sc.build("chain", 9, 9, 9, 9).m == 3
    assert sc.build("roads", 3, 4, 60, 5) == sc.generate(3, 4, 60, 5)


def test_analyse_shapes():
    a = ev.analyse(P._replace(deadline=12))
    assert a["plan"].T == 12 and a["best"].value == a["plan"].value and len(a["cumulative"]) == 13 and len(a["curve"]["curve"]) == C.T_MAX + 1
    assert a["naive_bound"] >= a["static_bound"] >= a["plan"].value
    b = ev.analyse(P._replace(method="naive"))
    assert b["plan"].value <= b["best"].value == ev.analyse(P)["plan"].value


def test_expanded_check_and_sizes():
    x = ev.expanded(P._replace(deadline=10))
    assert x["equal"] and x["nodes"] == 2 + 14 * 11 and x["static_nodes"] == 14 and x["scanned"] > x["ssp_scanned"]
    rows = ev.sizes(P, Ts=(5, 10), seeds=C.SIZE_SEEDS[:2])
    assert [r["T"] for r in rows] == [5, 10] and rows[0]["nodes"] < rows[1]["nodes"] and rows[0]["dinic"] < rows[1]["dinic"]
    lesson = ev.sizes(P._replace(net="chain"), Ts=(4, 8))
    assert lesson[0]["static_nodes"] == 4


def test_distribution_and_quickest_shapes():
    d = ev.distribution(P._replace(deadline=12), seeds=C.SWEEP_SEEDS[:3])
    assert d["n"] == 3 and d["equal"] == d["equal_no_hold"] == 3 and d["thetas"] == [3, 6, 9] and d["node_ratio"] == pytest.approx(13.14, abs=0.01)
    q = ev.quickest_table(P, ns=(30,), seeds=C.SWEEP_SEEDS[:3])
    assert q[0]["n"] == 30 and q[0]["mean_gap"] >= 0 and q[0]["total"] == 3


def test_thetas_and_labels():
    assert ev.thetas(20) == [5, 10, 15] and ev.thetas(5) == [1, 2, 3]
    assert ev.path_label(sc.chain(), (0, 2, 3, 1)) == "Sammelraum → A → B → Gate"
