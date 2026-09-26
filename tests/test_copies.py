"""Die aus den Vorgängern kopierten Bausteine (Zufallsgenerator, Successive Shortest Paths, Dinic) sind bewacht: dieselben Zahlen wie in ssp-demo und dinic-demo."""

import zf_dinic as dn
import zf_edmonds_karp as ek
import zf_scenario as sc
import zf_ssp as ssp


def _net(names, arcs):
    return sc.Net(tuple(names), tuple(names), tuple((0, 0) for _ in names), tuple((u, v, c, k, sc.K_ROAD) for u, v, c, k in arcs), 0, 1, "test")


def test_splitmix64_stream_is_the_portfolio_standard():
    rng = sc.SplitMix64(1)
    assert [rng.next() for _ in range(2)] == [10451216379200822465, 13757245211066428519]


def test_ssp_reproduces_the_diamond_of_ssp_demo():
    """ssp-demo, Raute mit Kosten: die erste Einheit fährt über S-A-B-T (3), die zweite nimmt A->B zurück und läuft S->B, A->T: 4 - 1 + 4 = 7, insgesamt 10."""
    net = _net(["S", "T", "A", "B"], [(0, 2, 1, 1), (0, 3, 1, 4), (2, 3, 1, 1), (2, 1, 1, 4), (3, 1, 1, 1)])
    res = ssp.ssp(net)
    assert (res.value, res.total, [r.price for r in res.rounds], [r.uses_back_arc for r in res.rounds]) == (2, 10, [3, 7], [False, True])


def test_max_length_stops_before_a_longer_round():
    net = _net(["S", "T", "A", "B"], [(0, 2, 1, 1), (0, 3, 1, 4), (2, 3, 1, 1), (2, 1, 1, 4), (3, 1, 1, 1)])
    res = ssp.ssp(net, max_length=5)
    assert (res.value, [r.price for r in res.rounds]) == (1, [3])
    assert ssp.ssp(net, max_length=7).value == 2 and ssp.ssp(net, max_length=2).value == 0


def test_dinic_and_edmonds_karp_reproduce_the_assignment_numbers():
    """dinic-demo, "Zuordnung als Fluss": eine Phase (Niveau 3) mit 5 Wegen, 69 durchsuchte Kanten gegen 100 bei Edmonds-Karp."""
    k = 4
    n = k + 1
    names = ["S", "T"] + [f"F{i + 1}" for i in range(n)] + [f"A{i + 1}" for i in range(n)]
    arcs = [(0, 2 + i, 1, 0) for i in range(n)]
    for i in range(n):
        arcs.append((2 + i, 2 + n + i, 1, 0))
        if i + 1 < n:
            arcs.append((2 + i + 1, 2 + n + i, 1, 0))
    arcs += [(2 + n + i, 1, 1, 0) for i in range(n)]
    net = _net(names, arcs)
    d = dn.dinic(net)
    assert (d.value, len(d.phases), d.phases[0].level, d.n_paths, d.scanned_total) == (5, 1, 3, 5, 69)
    e = ek.max_flow(net)
    assert (e.value, len(e.rounds), e.scanned_total) == (5, 5, 100)
