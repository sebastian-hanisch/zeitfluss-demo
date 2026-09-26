"""Szenario: ein Straßennetz zum Terminal als Flussnetz mit Fahrzeiten, und feste Lehrnetze.

Jede Straße hat eine **Kapazität** (Lkw, die pro Minute einfahren dürfen) und eine **Fahrzeit** (Minuten von der Einfahrt bis zur Ausfahrt). Das Netz hat eine Quelle S (Sammelraum am Autobahnanschluss) und eine Senke T (das Gate).
Alles ist ganzzahlig und läuft über einen eigenen Zufallsgenerator (SplitMix64 auf Python-Ints) statt über `numpy.random`: numpy garantiert keine über Versionen stabilen Zufallsströme, die CI installiert aber
wöchentlich die neueste Version. So sind Voreinstellungen, Seeds und jede im Text genannte Zahl auf Windows und Linux dieselben.

Die Kante ist wie in `ssp-demo` ein Tupel (u, v, Kapazität, Kosten, Art); die "Kosten" sind hier die Fahrzeiten, so dass das Successive-Shortest-Paths-Verfahren der Vorgänger den zeitwiederholten Fluss rechnet.
"""

from dataclasses import dataclass

_MASK = (1 << 64) - 1
MAP_W = 100

K_ROAD, K_LINK, K_GATE = range(3)         # Art einer Kante: Straße, Verbindung zwischen Sammelraum und Netz, Zufahrt zum Gate


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, n):
        """Ganzzahl in 0..n-1 (die Modulo-Verzerrung bei n <= 101 liegt um 1e-17)."""
        return self.next() % n


@dataclass(frozen=True)
class Net:
    names: tuple      # Anzeigename je Knoten (Hover)
    labels: tuple     # Kurzbeschriftung je Knoten (Karte)
    pos: tuple        # ((x, y), ...) je Knoten
    arcs: tuple       # ((u, v, Kapazität [Lkw je Minute], Fahrzeit [Minuten], Art), ...)
    s: int
    t: int
    kind: str = "roads"

    @property
    def n(self):
        return len(self.names)

    @property
    def m(self):
        return len(self.arcs)


def generate(layers, width, density, seed):
    """Zufallsnetz: S -> `layers` Schichten mit je `width` Kreuzungen -> T. Zwischen benachbarten Schichten gibt es die Gerade (gleiche Spalte, immer) und jede weitere Verbindung mit `density` Prozent;
    dazu Querstraßen innerhalb einer Schicht (Richtung zufällig, je Nachbarpaar mit halber Dichte). Kapazität 1..6 Lkw je Minute, Fahrzeit 1..5 Minuten; die Zufahrt zum Gate 2..6 und 1..2 Minuten,
    die Verbindungen vom Sammelraum 3..8 und 1..2. Die Zufallszahlen werden für jede mögliche Kante in fester Reihenfolge gezogen, egal ob sie existiert: die Dichte ändert nur, welche Straßen es gibt."""
    rng = SplitMix64(seed)
    names = ["Sammelraum", "Gate"] + [f"Kreuzung {i + 1}.{j + 1}" for i in range(layers) for j in range(width)]
    labels = ["S", "T"] + [f"{i + 1}.{j + 1}" for i in range(layers) for j in range(width)]
    node = lambda i, j: 2 + i * width + j
    xs = [(2 * j + 1) * MAP_W // (2 * width) for j in range(width)]
    ys = [88 - (76 * (i + 1)) // (layers + 1) for i in range(layers)]
    pos = [(MAP_W // 2, 96), (MAP_W // 2, 4)] + [(xs[j], ys[i]) for i in range(layers) for j in range(width)]
    arcs = []
    for j in range(width):
        arcs.append((0, node(0, j), 3 + rng.below(6), 1 + rng.below(2), K_LINK))
    for i in range(layers - 1):
        for j in range(width):
            for j2 in range(width):
                cap, tau, roll = 1 + rng.below(6), 1 + rng.below(5), rng.below(100)
                if j2 == j or roll < density:
                    arcs.append((node(i, j), node(i + 1, j2), cap, tau, K_ROAD))
    for i in range(layers):
        for j in range(width - 1):
            cap, tau, roll, flip = 1 + rng.below(4), 1 + rng.below(3), rng.below(100), rng.below(2)
            if roll < density // 2:
                u, v = (node(i, j), node(i, j + 1)) if flip else (node(i, j + 1), node(i, j))
                arcs.append((u, v, cap, tau, K_ROAD))
    for j in range(width):
        arcs.append((node(layers - 1, j), 1, 2 + rng.below(5), 1 + rng.below(2), K_GATE))
    return Net(tuple(names), tuple(labels), tuple(pos), tuple(arcs), 0, 1, "roads")


# --- feste Lehrnetze ------------------------------------------------------------------------------------------------------------

def _teaching(names, pos, arcs, kind):
    return Net(tuple(names), tuple(names), tuple(pos), tuple((u, v, c, k, K_ROAD) for u, v, c, k in arcs), 0, 1, kind)


def two_roads():
    """Zwei Straßen vom Sammelraum zum Gate: eine schnelle und enge (1 Lkw je Minute, 2 Minuten) und eine langsame und breite (3 Lkw je Minute, 6 Minuten).
    Bis zur Frist 5 lohnt nur die schnelle (V(T) = T - 1), ab Frist 6 kommt die breite dazu (V(T) = T - 1 + 3 (T - 5))."""
    return _teaching(["Sammelraum", "Gate"], [(15, 50), (85, 50)], [(0, 1, 1, 2), (0, 1, 3, 6)], "twoRoads")


def bottleneck():
    """Engpass: der kurze Weg S - A - B - T (Kapazität je Kante 4, 1, 4; Fahrzeit 1, 2, 1) hat in der Mitte eine schmale Brücke; daneben ein Umweg über C (Kapazität 2, Fahrzeit 3 + 4).
    Statisch fließen 3 Lkw je Minute (1 über die Brücke, 2 über den Umweg); dynamisch kommt der Umweg (Länge 7) erst ab Frist 7 an: V(T) = T - 3 für 4 <= T < 7, danach T - 3 + 2 (T - 6)."""
    names = ["Sammelraum", "Gate", "A", "B", "C"]
    pos = [(50, 92), (50, 8), (25, 62), (25, 36), (78, 50)]
    return _teaching(names, pos, [(0, 2, 4, 1), (2, 3, 1, 2), (3, 1, 4, 1), (0, 4, 2, 3), (4, 1, 2, 4)], "bottleneck")


def chain():
    """Kette: Sammelraum - A - B - Gate, jede Straße 2 Lkw je Minute und 3 Minuten: ein einziger Weg der Länge 9, der Fluss über die Zeit ist 2 (T - 8), sobald T >= 9."""
    names = ["Sammelraum", "Gate", "A", "B"]
    return _teaching(names, [(50, 92), (50, 8), (50, 64), (50, 36)], [(0, 2, 2, 3), (2, 3, 2, 3), (3, 1, 2, 3)], "chain")


def early():
    """Frühankunft: S -> A (5 Lkw je Minute, 1 Minute), S -> B (10, 3), A -> B (10, 1), A -> T (10, 3), B -> T (10, 1). Der kürzeste Weg S - A - B - T (3 Minuten) trägt 5 Lkw je Minute: bis Minute 3 kommen im besten Plan 5 Lkw an.
    Für eine späte Frist (T >= 5) ist es aber besser, den Weg zurückzunehmen: der Endfluss besteht aus S - A - T und S - B - T (je 4 Minuten, 5 und 10 Lkw je Minute) und liefert dabei mehr, bringt aber bis Minute 3 keinen einzigen Lkw ans Gate."""
    names = ["Sammelraum", "Gate", "A", "B"]
    return _teaching(names, [(50, 92), (50, 8), (22, 50), (78, 50)], [(0, 2, 5, 1), (0, 3, 10, 3), (2, 3, 10, 1), (2, 1, 10, 3), (3, 1, 10, 1)], "early")


LESSONS = {"tworoads": two_roads, "bottleneck": bottleneck, "chain": chain, "early": early}


def build(net, layers, width, density, seed):
    """Netz zu den Einstellungen; feste Lehrnetze ignorieren die Zufallsparameter."""
    if net != "roads":
        return LESSONS[net]()
    return generate(layers, width, density, seed)
