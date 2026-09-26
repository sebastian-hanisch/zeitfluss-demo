"""Fluss über die Zeit: Lehrnetze von Hand, Gleichheit mit dem zeitexpandierten Netz, Kapazität je Minute, Wegezerlegung, Konvexität von V(T), Schranken, schnellste Ankunft, Frühankunft, Kontrollen."""

import pytest

import zf_dynamic as dyn
import zf_expanded as ex
import zf_scenario as sc

NETS = [sc.generate(3, 4, 60, s) for s in range(100000, 100006)] + [sc.generate(2, 2, 30, 7), sc.generate(5, 5, 100, 3)]


def _v(net, T):
    return dyn.plan(net, T).value


def test_two_roads_by_hand():
    """Schnell und eng (1 je Minute, 2 Minuten), langsam und breit (3 je Minute, 6 Minuten): V(T) = T - 1 für 2 <= T <= 5, danach T - 1 + 3 (T - 5)."""
    net = sc.two_roads()
    assert [_v(net, T) for T in (1, 2, 3, 5, 6, 10)] == [0, 1, 2, 4, 8, 24]
    assert dyn.value_curve(net, 10)["rate"] == 4 and dyn.value_curve(net, 10)["shortest"] == 2


def test_bottleneck_by_hand():
    """Brücke (1 je Minute, Weg 4 Minuten) und Umweg (2 je Minute, 7 Minuten): V(T) = T - 3 für 4 <= T < 7, danach T - 3 + 2 (T - 6)."""
    net = sc.bottleneck()
    assert [_v(net, T) for T in (3, 4, 6, 7, 10)] == [0, 1, 3, 6, 15]
    assert dyn.value_curve(net, 10)["rate"] == 3


def test_chain_by_hand():
    net = sc.chain()
    assert [_v(net, T) for T in (8, 9, 12)] == [0, 2, 8] and dyn.plan(net, 12).n_paths == 1


def test_early_arrival_lesson_by_hand():
    """S-A-B-T (3 Minuten, 5 Lkw je Minute) ist der kürzeste Weg; der Plan für Frist >= 5 nimmt ihn zurück: S-A-T (5 je Minute) und S-B-T (10), je 4 Minuten, V(8) = 15 (8 - 3) = 75."""
    net = sc.early()
    assert _v(net, 4) == 15 and [(x, l) for _n, _a, x, l in dyn.plan(net, 4).paths] == [(5, 3), (5, 4)]
    p = dyn.plan(net, 8)
    assert p.value == 75 and [(x, l) for _n, _a, x, l in p.paths] == [(5, 4), (10, 4)] and p.rate == 15
    ratios = {th: (a, b) for th, a, b, _r in dyn.early_ratio(net, p.paths, 8)}
    assert ratios[3] == (0, 5) and ratios[4] == (15, 15) and ratios[8] == (75, 75)
    assert dyn.naive_greedy(net, 8)[0] == 55


@pytest.mark.parametrize("name", list(sc.LESSONS))
def test_plan_equals_the_time_expanded_max_flow_on_lessons(name):
    net = sc.LESSONS[name]()
    for T in range(1, 16):
        assert _v(net, T) == ex.max_flow(net, T)["value"] == ex.max_flow(net, T, hold=False)["value"], (name, T)


@pytest.mark.parametrize("net", NETS)
def test_plan_equals_the_time_expanded_max_flow_on_random_nets(net):
    for T in (6, 14, 25):
        assert _v(net, T) == ex.max_flow(net, T)["value"], T
    assert _v(net, 14) == ex.max_flow(net, 14, hold=False)["value"]


@pytest.mark.parametrize("net", NETS)
def test_value_formula_capacity_per_minute_and_decomposition(net):
    T = 18
    p = dyn.plan(net, T)
    assert p.value == (T + 1) * p.rate - sum(net.arcs[i][3] * p.flow[i] for i in range(net.m))         # V = (T + 1) |x| - Summe tau x
    assert all(0 <= p.flow[i] <= net.arcs[i][2] for i in range(net.m))
    rebuilt = [0] * net.m
    for nodes, arcs, x, l in p.paths:
        assert nodes[0] == net.s and nodes[-1] == net.t and l <= T and l == sum(net.arcs[i][3] for i in arcs)
        for i in arcs:
            rebuilt[i] += x
    assert tuple(rebuilt) == p.flow and sum(x for _n, _a, x, _l in p.paths) == p.rate
    for t in range(T + 1):
        load = dyn.load_at(net, p.paths, T, t)
        assert all(load[i] <= net.arcs[i][2] for i in range(net.m)), t
    rate, cum = dyn.arrivals(p.paths, T)
    assert cum[T] == p.value and sum(rate) == p.value


@pytest.mark.parametrize("net", NETS)
def test_value_curve_is_convex_monotone_and_below_the_static_bounds(net):
    c = dyn.value_curve(net, 40)
    v = c["curve"]
    assert all(v[T] == _v(net, T) for T in (0, 5, 12, 25, 40))
    assert all(b >= a for a, b in zip(v, v[1:])) and all(v[T + 1] - v[T] >= v[T] - v[T - 1] for T in range(1, 40))
    for T in range(1, 41):
        naive, bound = dyn.static_bounds(c["rate"], c["shortest"], T)
        assert v[T] <= bound <= naive


@pytest.mark.parametrize("net", NETS[:4])
def test_quickest_arrival_and_lower_bound(net):
    for n_trucks in (30, 120):
        T, lower = dyn.quickest(net, n_trucks)
        assert _v(net, T) >= n_trucks > _v(net, T - 1) and T >= lower


@pytest.mark.parametrize("net", NETS)
def test_early_ratio_never_above_one_and_exact_at_the_deadline(net):
    T = 20
    p = dyn.plan(net, T)
    rows = dyn.early_ratio(net, p.paths, T)
    assert all(a <= b for _th, a, b, _r in rows) and rows[-1][1] == rows[-1][2] == p.value


def test_the_negative_control_never_beats_the_optimum_and_can_lose():
    losses = 0
    for net in NETS:
        for T in (10, 20):
            best, naive = _v(net, T), dyn.plan(net, T, "naive")
            assert naive.value <= best and sum(x * (T - l + 1) for _n, _a, x, l in naive.paths) == naive.value
            assert all(0 <= naive.flow[i] <= net.arcs[i][2] for i in range(net.m))
            losses += naive.value < best
    assert losses >= 4
    assert dyn.naive_greedy(sc.chain(), 12)[0] == 8 and dyn.naive_greedy(sc.two_roads(), 10)[0] == 24


def test_expanded_network_sizes():
    net = sc.generate(3, 4, 60, 100000)
    for T in (5, 20):
        e = ex.expand(net, T)
        drives = sum(T + 1 - a[3] for a in net.arcs if a[3] <= T + 1)
        assert e.nodes == 2 + net.n * (T + 1) and e.arcs == drives + net.n * T + 2 * (T + 1)
        assert ex.expand(net, T, hold=False).arcs == drives + 2 * (T + 1)


def test_empty_horizon_and_unreachable_gate():
    net = sc.chain()
    p = dyn.plan(net, 3)
    assert p.value == 0 and p.paths == () and p.rate == 0
    assert dyn.quickest(sc._teaching(["S", "T"], [(0, 0), (1, 1)], [], "x"), 5) == (None, None)
