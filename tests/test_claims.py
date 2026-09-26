"""Jede Zahl, die README, Hilfetexte und Beispieltexte nennen, ist hier belegt (Straßennetz 3 Schichten x 4 Kreuzungen, Dichte 60, Seed 1, Frist 20; feste Netze ab Seed 100000).
Die Rechnung ist ganzzahlig und deterministisch: Werte, Weg- und Kantenzahlen sind auf allen Plattformen dieselben; Mittel über Netze werden mit Bändern geprüft."""

import pytest

import zf_constants as C
import zf_dynamic as dyn
import zf_evaluation as ev
import zf_expanded as ex
import zf_scenario as sc

P = ev.DEFAULT_PARAMS


def _params(name):
    p = C.PRESETS[name]
    return ev.Params(p["net"], p["layers"], p["width"], p["density"], p["method"], p["deadline"], p["trucks"], p["seed"])


def test_the_default_network_and_the_plan():
    """14 Knoten, 34 Straßen; Frist 20: V = 222 Lkw aus 11 Wegen bei statischem Fluss 19 je Minute, kürzester Weg 5 Minuten; f* T = 380 (71 % zu viel), Schranke 304; 100 Lkw frühestens nach 14 Minuten (Untergrenze 10)."""
    a = ev.analyse(P)
    net, plan = a["net"], a["plan"]
    assert (net.n, net.m) == (14, 34)
    assert (plan.value, plan.n_paths, a["curve"]["rate"], a["curve"]["shortest"]) == (222, 11, 19, 5)
    assert (a["naive_bound"], a["static_bound"]) == (380, 304) and a["naive_bound"] / plan.value == pytest.approx(1.71, abs=0.005)
    assert a["quick"] == (14, 10)
    assert plan.scanned == 716


def test_the_time_expanded_network_and_the_effort():
    """Zeitnetz mit 296 Knoten und 950 Kanten, Max-Flow ebenfalls 222 (mit und ohne Warte-Kanten); Dinic scannt 7 090 Kanten gegen 716 im Straßennetz."""
    x = ev.expanded(P)
    assert (x["nodes"], x["arcs"], x["expanded_value"], x["no_hold_value"], x["equal"]) == (296, 950, 222, 222, True)
    assert (x["scanned"], x["ssp_scanned"]) == (7090, 716)


def test_early_arrival_in_the_default_network():
    """Der Plan für Frist 20 liefert bei Frist 8 nur 14 von 19 Lkw (73,7 %), bei Frist 10 38 von 42 (90,5 %), der Plan verliert genau bei den Fristen 6 bis 13 (bei 13 noch 89 statt 90), ab Frist 14 stimmt er mit dem besten Plan überein."""
    a = ev.analyse(P)
    rows = {th: (x, y, r) for th, x, y, r in a["early"]}
    assert rows[5][:2] == (2, 2) and rows[8][:2] == (14, 19) and rows[10][:2] == (38, 42) and rows[8][2] == pytest.approx(0.737, abs=0.001) and rows[10][2] == pytest.approx(0.905, abs=0.001)
    assert [th for th, r in rows.items() if r[2] is not None and r[2] < 1] == [6, 7, 8, 9, 10, 11, 12, 13] and rows[13][:2] == (89, 90)


def test_two_roads_by_hand_in_the_texts():
    """V(5) = 4, V(6) = 8, V(10) = 24 gegen 40 statisch; 100 Lkw brauchen 29 Minuten (Untergrenze 26)."""
    a = ev.analyse(_params("🛣️ Zwei Straßen"))
    assert [a["curve"]["curve"][T] for T in (5, 6, 10)] == [4, 8, 24] and a["naive_bound"] == 40 and a["quick"] == (29, 26)
    assert a["naive_bound"] / a["plan"].value == pytest.approx(5 / 3, abs=0.001)


def test_bottleneck_by_hand_in_the_texts():
    """V(4) = 1, V(7) = 6, V(10) = 15 gegen 30 statisch (das Doppelte)."""
    a = ev.analyse(_params("🚧 Engpass"))
    assert [a["curve"]["curve"][T] for T in (4, 7, 10)] == [1, 6, 15] and a["naive_bound"] == 30 == 2 * a["plan"].value


def test_early_lesson_by_hand_in_the_texts():
    """V(8) = 75 mit S-A-T und S-B-T (je 4 Minuten) gegen 55 ohne Rücknahme; bis Minute 3 im besten Plan 5 Lkw, im Plan für Frist 8 keiner."""
    a = ev.analyse(_params("⏱️ Frühankunft"))
    assert a["plan"].value == 75 and a["naive_bound"] == 120
    assert [(x, l) for _n, _a, x, l in a["plan"].paths] == [(5, 4), (10, 4)] and dyn.naive_greedy(a["net"], 8)[0] == 55
    assert {th: (x, y) for th, x, y, _r in a["early"]}[3] == (0, 5)


def test_chain_by_hand_in_the_texts():
    """Ein Weg mit 9 Minuten: bis Minute 8 nichts, bei Frist 12 acht Lkw gegen 24 statisch (das Dreifache); 100 Lkw brauchen 58 Minuten = Untergrenze."""
    a = ev.analyse(_params("🔗 Kette"))
    assert a["curve"]["curve"][8] == 0 and a["plan"].value == 8 and a["naive_bound"] == 24 == 3 * a["plan"].value and a["quick"] == (58, 58)


def test_large_and_small_deadline():
    """Frist 60: 982 Lkw (statisch 1 140, 16 % zu viel), Zeitnetz 856 Knoten und 2 950 Kanten, Dinic 24 890 gegen 716 (35-fach). Frist 8: 19 Lkw gegen 152 (das Achtfache)."""
    big = ev.analyse(_params("⌛ Große Frist"))
    assert big["plan"].value == 982 and big["naive_bound"] == 1140 and big["naive_bound"] / 982 == pytest.approx(1.16, abs=0.005)
    x = ev.expanded(_params("⌛ Große Frist"))
    assert (x["nodes"], x["arcs"], x["scanned"], x["ssp_scanned"]) == (856, 2950, 24890, 716) and x["scanned"] / x["ssp_scanned"] == pytest.approx(34.8, abs=0.1)
    small = ev.analyse(_params("⚡ Kleine Frist"))
    assert small["plan"].value == 19 and small["naive_bound"] == 152 == 8 * small["plan"].value


def test_the_negative_control():
    """Ohne Rücknahme 210 statt 222 Lkw (94,6 %), 12 statt 11 Wege."""
    a = ev.analyse(_params("🧪 Ohne Rücknahme"))
    assert (a["plan"].value, a["best"].value, a["plan"].n_paths, a["best"].n_paths) == (210, 222, 12, 11) and a["plan"].value / a["best"].value == pytest.approx(0.946, abs=0.0005)


def test_size_and_effort_by_deadline():
    """Erste 5 feste Netze, Mittel: Knoten 86 / 156 / 296 / 576 / 856 bei Fristen 5 / 10 / 20 / 40 / 60 gegen 14; Dinic 590 / 4 594 / 25 017 / 72 614 / 117 928 gescannte Kanten, das statische Verfahren 125 / 415 / 483 / 483 / 483."""
    rows = ev.sizes(P)
    assert [r["T"] for r in rows] == [5, 10, 20, 40, 60]
    assert [round(r["nodes"]) for r in rows] == [86, 156, 296, 576, 856] and all(r["static_nodes"] == 14 for r in rows)
    assert [round(r["dinic"]) for r in rows] == [590, 4594, 25017, 72614, 117928]
    assert [round(r["ssp"]) for r in rows] == [125, 415, 483, 483, 483]
    assert rows[2]["dinic"] / rows[2]["ssp"] == pytest.approx(51.8, abs=0.1) and rows[4]["dinic"] / rows[4]["ssp"] == pytest.approx(244.1, abs=0.2)


def test_distribution_over_40_nets_at_deadline_20():
    """Der Satz gilt in 40 von 40 Netzen (mit und ohne Warte-Kanten); Zeitnetz 21,1-mal so viele Knoten (T + 1) und 28,4-mal so viele Kanten; Dinic im Mittel 37,9-faches Aufwandsverhältnis; f* T im Mittel 51 % über V(T), die Schranke 18 %;
    Frühankunft: Minute 5 im Mittel 66,4 % (schlechtestes Netz 0 %, 13 von 23 Netzen mit Verlust), Minute 10 98,3 % (schlechtestes 71,4 %, 11 von 40), Minute 15 kein Verlust; Negativkontrolle unter dem Optimum in 23 von 40 (Mittel 98,1 %, schlechtestes 87,1 %)."""
    d = ev.distribution(P)
    assert (d["n"], d["equal"], d["equal_no_hold"]) == (40, 40, 40)
    assert d["node_ratio"] == pytest.approx(21.14, abs=0.01) and d["arc_ratio"] == pytest.approx(28.4, abs=0.1) and d["scan_ratio"] == pytest.approx(37.9, abs=0.3)
    assert d["naive_bound"] == pytest.approx(1.512, abs=0.005) and d["static_bound"] == pytest.approx(1.182, abs=0.005)
    assert d["thetas"] == [5, 10, 15]
    assert 1 - d["early_mean"][10] == pytest.approx(0.018, abs=0.0005) and 1 - d["early_mean"][5] == pytest.approx(0.34, abs=0.005) and 1 - d["naive_mean"] == pytest.approx(0.019, abs=0.0005) and 1 - d["naive_min"] == pytest.approx(0.129, abs=0.0005)
    assert d["early_mean"][5] == pytest.approx(0.664, abs=0.002) and d["early_min"][5] == 0.0 and d["early_share"][5] == (13, 23)
    assert d["early_mean"][10] == pytest.approx(0.9825, abs=0.0005) and d["early_min"][10] == pytest.approx(0.714, abs=0.001) and d["early_share"][10] == (11, 40)
    assert d["early_mean"][15] == 1.0 and d["early_share"][15] == (0, 40)
    assert d["naive_lost"] == 23 and d["naive_mean"] == pytest.approx(0.981, abs=0.001) and d["naive_min"] == pytest.approx(0.871, abs=0.001)


def test_distribution_at_other_deadlines():
    """Bei Frist 10 überschätzt f* T im Mittel um das 3,3-Fache, bei Frist 40 um 20 %; die Frühankunft ist auch dort in 40 von 40 Netzen exakt gleich dem Zeitnetz."""
    d10, d40 = ev.distribution(P._replace(deadline=10)), ev.distribution(P._replace(deadline=40))
    assert d10["naive_bound"] == pytest.approx(3.278, abs=0.01) and d40["naive_bound"] == pytest.approx(1.202, abs=0.005)
    assert d10["equal"] == d40["equal"] == 40 and d10["equal_no_hold"] == d40["equal_no_hold"] == 40 and d40["early_share"][30] == (0, 40)
    assert d10["scan_ratio"] == pytest.approx(10.0, abs=0.1) and d40["scan_ratio"] == pytest.approx(91.2, abs=0.5)                       # Aufwandsverhältnis Dinic / zeitwiederholt bei Frist 10 / 20 / 40: 10,0 / 37,9 / 91,2
    assert d10["arc_ratio"] == pytest.approx(13.4, abs=0.1) and d40["arc_ratio"] == pytest.approx(58.2, abs=0.1)
    assert d10["static_bound"] == pytest.approx(1.772, abs=0.005) and d40["static_bound"] == pytest.approx(1.072, abs=0.005)
    assert d10["early_share"][5] == (12, 23) and d10["early_mean"][5] == pytest.approx(0.693, abs=0.002)                                # Frist 10: Minute 5 im Mittel 69,3 %, Minute 2 kann noch kein Lkw ankommen
    assert d10["early_mean"][2] is None


def test_quickest_arrival_over_40_nets():
    """Schnellste Ankunft von 50 / 100 / 200 Lkw im Mittel nach 10,5 / 13,8 / 20,8 Minuten, Untergrenze 8,1 / 11,6 / 18,4: gut zwei Minuten Lücke, in keinem Netz gleich."""
    rows = ev.quickest_table(P)
    assert [r["n"] for r in rows] == [50, 100, 200]
    assert [round(r["mean_T"], 1) for r in rows] == [10.5, 13.8, 20.8] and [round(r["mean_lower"], 1) for r in rows] == [8.1, 11.6, 18.4]
    assert all(2.0 <= r["mean_gap"] <= 2.5 and r["equal"] == 0 for r in rows)


def test_ford_fulkerson_on_more_nets_than_the_texts_mention():
    """Der Satz von Ford und Fulkerson auf 60 Netzen über mehrere Größen und Fristen (Sicherung gegen Off-by-one der Diskretisierung)."""
    checked = 0
    for layers in (2, 4):
        for width in (2, 3, 5):
            for seed in range(100000, 100005):
                net = sc.generate(layers, width, 70, seed)
                for T in (7, 16):
                    assert dyn.plan(net, T).value == ex.max_flow(net, T)["value"]
                    checked += 1
    assert checked == 60
