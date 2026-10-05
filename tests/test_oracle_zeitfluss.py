"""Orakel: V(T) des zeitwiederholten Flusses gegen (a) ein lineares Programm über statische Flüsse, max (T+1)|x| - Summe tau x (scipy/HiGHS),
(b) ein eigenes zeitexpandiertes Netz mit networkx; dazu eine Nachsimulation des Plans Minute für Minute (Kapazität je Minute, Ankünfte, Einfahrtraten)."""

import itertools
import random

import numpy as np
import pytest

import zf_dynamic as dyn
import zf_scenario as sc

linprog = pytest.importorskip("scipy.optimize").linprog
nx = pytest.importorskip("networkx")


def _lp_value(net, T):
    a = np.zeros((net.n, net.m))
    for i, (u, v, *_r) in enumerate(net.arcs):
        a[u, i] -= 1
        a[v, i] += 1
    inner = [v for v in range(net.n) if v not in (net.s, net.t)]
    c = np.array([arc[3] for arc in net.arcs], float) - (T + 1) * a[net.t]
    r = linprog(c, A_eq=a[inner], b_eq=np.zeros(len(inner)), bounds=[(0, arc[2]) for arc in net.arcs], method="highs")
    return max(0, int(round(-r.fun)))


def _nx_expanded(net, T):
    g = nx.DiGraph()
    for i, (u, v, c, tau, _k) in enumerate(net.arcs):
        for k in range(T + 1 - tau):
            g.add_edge(("v", u, k), ("e", i, k), capacity=c)
            g.add_edge(("e", i, k), ("v", v, k + tau))
    for v in range(net.n):
        for k in range(T):
            g.add_edge(("v", v, k), ("v", v, k + 1))
    for k in range(T + 1):
        g.add_edge("S", ("v", net.s, k))
        g.add_edge(("v", net.t, k), "T")
    return nx.maximum_flow_value(g, "S", "T")


def _random_net(rng):
    n = rng.randint(3, 6)
    arcs = [(rng.randrange(n), rng.randrange(n), rng.randint(1, 5), rng.randint(1, 4), sc.K_ROAD) for _ in range(rng.randint(2, 3 * n))]
    arcs = [a for a in arcs if a[0] != a[1]] or [(0, 1, 2, 2, sc.K_ROAD)]
    names = tuple(str(i) for i in range(n))
    return sc.Net(names, names, tuple((0, 0) for _ in range(n)), tuple(arcs), 0, 1, "roads")


def _simulate(net, paths, T):
    arrivals, loads = [0] * (T + 1), {}
    for _nodes, arcs, x, length in paths:
        for start in range(T - length + 1):
            t = start
            for i in arcs:
                loads[(i, t)] = loads.get((i, t), 0) + x
                t += net.arcs[i][3]
            arrivals[t] += x
    return arrivals, loads


def test_plan_value_matches_lp_and_own_time_expansion():
    rng = random.Random(3)
    nets = [_random_net(rng) for _ in range(25)] + [sc.generate(rng.randint(2, 3), rng.randint(2, 3), 60, rng.randrange(10 ** 6)) for _ in range(6)] + [f() for f in sc.LESSONS.values()]
    for net in nets:
        for T in (0, 2, 5, 9):
            plan = dyn.plan(net, T)
            assert plan.value == _lp_value(net, T) == _nx_expanded(net, T)
            arrivals, loads = _simulate(net, plan.paths, T)
            assert sum(arrivals) == plan.value
            assert all(v <= net.arcs[i][2] for (i, _t), v in loads.items())
            assert dyn.arrivals(plan.paths, T)[1] == list(itertools.accumulate(arrivals))
            assert dyn.plan(net, T, "naive").value <= plan.value
