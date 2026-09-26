"""Das zeitexpandierte Netz: die exakte, aber große Gegenprobe zum zeitwiederholten Fluss.

Jede Kreuzung v wird zu T + 1 Knoten (v, 0) ... (v, T), einen je Minute. Eine Straße (u, v) mit Kapazität c und Fahrzeit tau wird zu den Kanten (u, k) -> (v, k + tau) für alle k mit k + tau <= T, jede mit Kapazität c
(c Lkw dürfen pro Minute einfahren). **Warte-Kanten** (v, k) -> (v, k + 1) ohne Grenze lassen Lkw an einer Kreuzung stehen. Ein Verteiler verbindet den Sammelraum zu allen Minuten mit der Quelle, das Gate zu allen Minuten mit der Senke.
Der maximale Fluss in diesem Netz (Dinic aus `dinic-demo`) ist die größte Zahl Lkw, die bis zur Frist T ankommen kann - für jedes Netz, ohne jede Annahme.
Das Netz hat (T + 1) mal so viele Knoten wie das Straßennetz und wächst mit der Frist; der zeitwiederholte Fluss rechnet auf dem kleinen Netz.
"""

from dataclasses import dataclass

import zf_dinic as dn
import zf_scenario as sc


@dataclass(frozen=True)
class Expanded:
    net: object            # das expandierte Netz (Quelle 0, Senke 1, dann (v, k) auf 2 + v (T + 1) + k)
    T: int
    hold: bool

    @property
    def nodes(self):
        return self.net.n

    @property
    def arcs(self):
        return self.net.m


def expand(net, T, hold=True):
    big = sum(c for (_u, _v, c, _k, _a) in net.arcs) * (T + 1) + 1
    idx = lambda v, k: 2 + v * (T + 1) + k
    n = 2 + net.n * (T + 1)
    arcs = []
    for u, v, c, tau, _kind in net.arcs:
        for k in range(0, T + 1 - tau):
            arcs.append((idx(u, k), idx(v, k + tau), c, 0, sc.K_ROAD))
    if hold:
        for v in range(net.n):
            for k in range(T):
                arcs.append((idx(v, k), idx(v, k + 1), big, 0, sc.K_ROAD))
    for k in range(T + 1):
        arcs.append((0, idx(net.s, k), big, 0, sc.K_LINK))
        arcs.append((idx(net.t, k), 1, big, 0, sc.K_GATE))
    names = tuple("S*" if i == 0 else "T*" if i == 1 else f"{(i - 2) // (T + 1)}@{(i - 2) % (T + 1)}" for i in range(n))
    big_net = sc.Net(names, names, (), tuple(arcs), 0, 1, "expanded")
    return Expanded(big_net, T, hold)


def max_flow(net, T, hold=True):
    """Maximaler Fluss im zeitexpandierten Netz: Wert, Knoten, Kanten, gescannte Kanten (Dinic)."""
    ex = expand(net, T, hold)
    res = dn.dinic(ex.net, keep_flows=False)
    return dict(value=res.value, nodes=ex.nodes, arcs=ex.arcs, scanned=res.scanned_total, phases=len(res.phases))
