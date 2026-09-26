"""Fluss über die Zeit: der zeitwiederholte Fluss (Ford und Fulkerson 1958) für einen Sammelraum S und ein Gate T.

**Frage:** Wie viele Lkw können innerhalb der Frist T (in ganzen Minuten) am Gate ankommen, wenn jede Straße höchstens `Kapazität` Lkw je Minute einfahren lässt und jede Fahrt `Fahrzeit` Minuten dauert?

**Satz (Ford und Fulkerson):** Man muss dafür kein Netz über die Zeit bauen. Man rechnet **einen** statischen Fluss, der die Fahrzeit als Kosten je Lkw behandelt, zerlegt ihn in Wege und **wiederholt** jeden Weg P mit seiner Menge x_P
in jeder Minute, in der ein Lkw noch rechtzeitig ankommt: Einfahrt zu den Zeiten 0 bis T - l_P, wenn l_P die Fahrzeit des Weges ist. Das sind T - l_P + 1 Wiederholungen, also

    V(T) = Summe_P x_P (T - l_P + 1)         (nur Wege mit l_P <= T).

Der beste statische Fluss ist der der **Successive Shortest Paths** aus `ssp-demo` (Kosten = Fahrzeit): jede Runde füllt den zeitlich kürzesten Weg im Restgraphen (die Rundenlängen steigen), und man nimmt alle Runden mit l <= T.
Weil die Rundenlängen für jedes T dieselben sind, liefert **ein** Lauf die Werte V(T) für alle Fristen. Die Zerlegung des *Endflusses* in Wege ist dagegen eine andere als die der Runden (Rücknahmen ändern Wege) - das ist der Grund,
warum der Plan für Frist T bei einer früheren Frist weniger liefern kann als der beste Plan für diese frühere Frist.

Aufwand in gescannten Kanten, nie Sekunden.
"""

import heapq
from dataclasses import dataclass

import zf_ssp as ssp

INF = float("inf")


@dataclass(frozen=True)
class Plan:
    T: int
    rounds: tuple          # (Fahrzeit l, Menge x, nutzt Rücknahmekante) je Runde mit l <= T, in der Reihenfolge des Verfahrens
    flow: tuple            # statischer Fluss je Netzkante (Lkw je Minute)
    paths: tuple           # Zerlegung des Flusses: (Knotenfolge, Netzkanten, Menge x_P, Fahrzeit l_P), nach Fahrzeit sortiert
    value: int             # V(T): Lkw, die bis zur Frist ankommen
    scanned: int           # gescannte Kanten des Verfahrens (Successive Shortest Paths)
    rate: int              # statischer Fluss je Minute (Summe der Mengen)

    @property
    def n_paths(self):
        return len(self.paths)


def value_from_rounds(rounds, T):
    """V(T) aus den Runden (Länge, Menge, ...): Summe x (T - l + 1) über alle Runden mit l <= T."""
    return sum(x * (T - l + 1) for l, x, *_ in rounds if l <= T)


def all_rounds(net):
    """Alle Runden des Verfahrens bis zum maximalen statischen Fluss: ((Fahrzeit, Menge, Rücknahme), ...), nicht fallend in der Fahrzeit."""
    res = ssp.ssp(net, "dijkstra", keep_trace=False)
    return tuple((r.price, r.bottleneck, r.uses_back_arc) for r in res.rounds), res


def decompose(net, flow):
    """Zerlegung eines statischen Flusses ohne Kreise in Wege von S nach T: ((Knoten, Kanten, Menge, Fahrzeit), ...), nach Fahrzeit und Kantenfolge sortiert.
    Ein kostenminimaler Fluss mit positiven Fahrzeiten enthält keinen Kreis; wegen der Flusserhaltung führt dann jeder Schritt entlang einer Kante mit Fluss zum Gate."""
    out = [[] for _ in range(net.n)]
    for i, (u, *_r) in enumerate(net.arcs):
        if flow[i] > 0:
            out[u].append(i)
    f = list(flow)
    paths = []
    while any(f[i] > 0 for i in out[net.s]):
        node, arcs, seen = net.s, [], {net.s}
        while node != net.t:
            i = next(i for i in out[node] if f[i] > 0)
            arcs.append(i)
            node = net.arcs[i][1]
            assert node not in seen, "Kreis im Fluss"
            seen.add(node)
        amount = min(f[i] for i in arcs)
        for i in arcs:
            f[i] -= amount
        paths.append(((net.s,) + tuple(net.arcs[i][1] for i in arcs), tuple(arcs), amount, sum(net.arcs[i][3] for i in arcs)))
    return tuple(sorted(paths, key=lambda p: (p[3], p[1])))


def plan(net, T, method="ssp"):
    """Der zeitwiederholte Fluss für die Frist T. `method`: 'ssp' (Successive Shortest Paths mit Rücknahmekanten, optimal) oder 'naive' (nur Vorwärtskanten, Negativkontrolle)."""
    if method == "naive":
        return plan_naive(net, T)
    res = ssp.ssp(net, "dijkstra", keep_trace=False, max_length=T)
    rounds = tuple((r.price, r.bottleneck, r.uses_back_arc) for r in res.rounds)
    paths = decompose(net, res.flow)
    value = sum(x * (T - l + 1) for _n, _a, x, l in paths)
    assert value == value_from_rounds(rounds, T)
    return Plan(T, rounds, res.flow, paths, value, res.scanned_total, sum(x for _n, _a, x, _l in paths))


def value_curve(net, t_max):
    """V(T) für T = 0 .. t_max aus einem einzigen Lauf, dazu die statische Rate f* (maximaler statischer Fluss) und die kürzeste Fahrzeit."""
    rounds, res = all_rounds(net)
    curve = [value_from_rounds(rounds, T) for T in range(t_max + 1)]
    rate = sum(x for _l, x, _b in rounds)
    return dict(curve=curve, rate=rate, shortest=rounds[0][0] if rounds else None, rounds=rounds)


def quickest(net, n_trucks, limit=100000):
    """Kleinste Frist T, bis zu der n_trucks Lkw ankommen können (V(T) >= n_trucks); None, wenn es keinen Weg gibt. Rückgabe (T, Untergrenze), Untergrenze = ceil(n / f*) + l_min - 1."""
    rounds, _res = all_rounds(net)
    if not rounds:
        return None, None
    rate = sum(x for _l, x, _b in rounds)
    lower = -(-n_trucks // rate) + rounds[0][0] - 1
    T = rounds[0][0]
    while value_from_rounds(rounds, T) < n_trucks and T < limit:
        T += 1
    return T, lower


def arrivals(paths, T):
    """Ankünfte je Minute 0 .. T unter dem Plan (Summe der Mengen der Wege, deren Fahrzeit <= Minute ist) und kumuliert: Listen (Rate, kumuliert)."""
    rate = [sum(x for _n, _a, x, l in paths if l <= th) for th in range(T + 1)]
    cum, run = [], 0
    for r in rate:
        run += r
        cum.append(run)
    return rate, cum


def early_ratio(net, paths, T, deadlines=None):
    """Wie viel liefert der Plan für die Frist T bei früheren Fristen theta gegenüber dem dort besten Plan: Liste (theta, A_T(theta), V(theta), Verhältnis)."""
    rounds, _res = all_rounds(net)
    _rate, cum = arrivals(paths, T)
    out = []
    for th in (range(1, T + 1) if deadlines is None else deadlines):
        best = value_from_rounds(rounds, th)
        got = cum[th]
        out.append((th, got, best, (got / best) if best else None))
    return out


def load_at(net, paths, T, t):
    """Einfahrtrate je Netzkante zur Minute t unter dem Plan: Weg P fährt zu den Zeiten 0..T-l_P in die Kante ein, die nach `offset` Minuten Fahrt auf seinem Weg liegt, also zur Minute t genau dann, wenn 0 <= t - offset <= T - l_P."""
    load = [0] * net.m
    for _nodes, arcs, x, l in paths:
        offset = 0
        for i in arcs:
            if 0 <= t - offset <= T - l:
                load[i] += x
            offset += net.arcs[i][3]
    return load


def naive_greedy(net, T):
    """Negativkontrolle: kürzeste Wege (nach Fahrzeit) nur über Vorwärtskanten füllen, ohne je Fluss zurückzunehmen. Rückgabe (Wert V, Runden (Fahrzeit, Menge), Wege, Fluss je Kante, gescannte Kanten)."""
    res = [c for (_u, _v, c, _k, _a) in net.arcs]
    adj = [[] for _ in range(net.n)]
    for i, (u, *_r) in enumerate(net.arcs):
        adj[u].append(i)
    value, rounds, paths, scanned = 0, [], [], 0
    while True:
        dist = [INF] * net.n
        parent = [-1] * net.n
        dist[net.s] = 0
        heap = [(0, net.s)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            for i in adj[u]:
                scanned += 1
                v, tau = net.arcs[i][1], net.arcs[i][3]
                if res[i] > 0 and d + tau < dist[v]:
                    dist[v] = d + tau
                    parent[v] = i
                    heapq.heappush(heap, (d + tau, v))
        if dist[net.t] == INF or dist[net.t] > T:
            break
        path, v = [], net.t
        while v != net.s:
            i = parent[v]
            path.append(i)
            v = net.arcs[i][0]
        path.reverse()
        amount = min(res[i] for i in path)
        for i in path:
            res[i] -= amount
        value += amount * (T - dist[net.t] + 1)
        rounds.append((dist[net.t], amount))
        paths.append(((net.s,) + tuple(net.arcs[i][1] for i in path), tuple(path), amount, dist[net.t]))
    flow = tuple(net.arcs[i][2] - res[i] for i in range(net.m))
    return value, tuple(rounds), tuple(sorted(paths, key=lambda p: (p[3], p[1]))), flow, scanned


def plan_naive(net, T):
    value, rounds, paths, flow, scanned = naive_greedy(net, T)
    return Plan(T, tuple((l, x, False) for l, x in rounds), flow, paths, value, scanned, sum(x for l, x in rounds))


def static_bounds(rate, shortest, T):
    """Statische Schranken: naiv f* T (ignoriert die Fahrzeit) und f* (T - l_min + 1) (jede Einfahrzeit höchstens bis T - l_min)."""
    return rate * T, (rate * (T - shortest + 1) if shortest is not None and T >= shortest else 0)
