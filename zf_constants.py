"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Fluss über die Zeit: wie viele Lkw kommen in T Minuten am Gate an?"."""

# --- Regler ---------------------------------------------------------------------------------------------------------------------
LAYERS_MIN, LAYERS_MAX, DEFAULT_LAYERS = 2, 5, 3      # Schichten von Kreuzungen zwischen Sammelraum und Gate
WIDTH_MIN, WIDTH_MAX, DEFAULT_WIDTH = 2, 5, 4         # Kreuzungen je Schicht
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 30, 100, 60   # Anteil weiterer Straßen zwischen benachbarten Schichten in Prozent
T_MIN, T_MAX, DEFAULT_T = 5, 60, 20                   # Frist in Minuten
TRUCKS_MIN, TRUCKS_MAX, DEFAULT_TRUCKS = 10, 500, 100  # Lkw für die schnellste Ankunft
DEFAULT_SEED = 1
SEED_MAX = 2_000_000_000

NETS = {
    "roads": "Straßennetz zum Gate",
    "tworoads": "Zwei Straßen (schnell und eng, langsam und breit)",
    "bottleneck": "Engpass (Brücke und Umweg)",
    "chain": "Kette (ein einziger Weg)",
    "early": "Frühankunft (Rücknahme lohnt erst spät)",
}
DEFAULT_NET = "roads"
FIXED_NETS = ("tworoads", "bottleneck", "chain", "early")
METHODS = {"ssp": "Zeitwiederholter Fluss (Successive Shortest Paths, mit Rücknahme)", "naive": "Nur Vorwärtskanten (Negativkontrolle, ohne Rücknahme)"}
DEFAULT_METHOD = "ssp"
DEADLINE_T = 20

# --- feste Seed-Mengen (dieselben wie in den Flussdemos; unabhängig vom Nutzer-Seed) ---------------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SIZE_TS = (5, 10, 20, 40, 60)
SIZE_SEEDS = DIST_SEEDS[:5]

COLORS = {"plan": "#2ca02c", "best": "#7f7f7f", "static": "#d62728", "bound": "#ff7f0e", "dinic": "#1f77b4", "ssp": "#2ca02c", "naive": "#9467bd", "node": "#111111", "gate": "#d62728", "source": "#1f77b4"}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net=DEFAULT_NET, layers=DEFAULT_LAYERS, width=DEFAULT_WIDTH, density=DEFAULT_DENSITY, method=DEFAULT_METHOD, deadline=DEFAULT_T, trucks=DEFAULT_TRUCKS, seed=DEFAULT_SEED)
PRESETS = {
    "🚚 Straßennetz": {**_BASE},
    "🛣️ Zwei Straßen": {**_BASE, "net": "tworoads", "deadline": 10},
    "🚧 Engpass": {**_BASE, "net": "bottleneck", "deadline": 10},
    "⏱️ Frühankunft": {**_BASE, "net": "early", "deadline": 8},
    "🔗 Kette": {**_BASE, "net": "chain", "deadline": 12},
    "⌛ Große Frist": {**_BASE, "deadline": 60},
    "⚡ Kleine Frist": {**_BASE, "deadline": 8},
    "🧪 Ohne Rücknahme": {**_BASE, "method": "naive"},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (Lehrnetze von Hand, Straßennetz über die Seeds der Presets)
PRESET_HELP = {
    "🚚 Straßennetz": "Ein Schichtennetz mit 14 Knoten und 34 Straßen (3 Schichten mit je 4 Kreuzungen). In 20 Minuten können bis zu 222 Lkw am Gate ankommen, obwohl das Netz statisch 19 Lkw je Minute durchlässt: 19 mal 20 = 380 wären 71 % zu viel, weil der kürzeste Weg 5 Minuten braucht und lange Umwege spät ankommen. Der Plan besteht aus 11 Wegen. Das zeitexpandierte Netz hat 296 Knoten und 950 Kanten; sein Max-Flow ist ebenfalls 222, Dinic scannt darin 7 090 Kanten gegen 716 im Straßennetz. 100 Lkw sind frühestens nach 14 Minuten am Gate (Untergrenze aus dem statischen Fluss: 10).",
    "🛣️ Zwei Straßen": "Eine schnelle enge Straße (1 Lkw je Minute, 2 Minuten) und eine langsame breite (3 Lkw je Minute, 6 Minuten). Bis Frist 5 trägt nur die schnelle (4 Lkw), ab Frist 6 kommt die breite dazu (8 Lkw); bei Frist 10 kommen 24 Lkw an, statisch (4 mal 10 = 40) wären es zwei Drittel mehr. 100 Lkw brauchen 29 Minuten (Untergrenze 26).",
    "🚧 Engpass": "Der kurze Weg (4 Minuten) hat eine Brücke mit 1 Lkw je Minute, daneben ein Umweg mit 2 Lkw je Minute und 7 Minuten. Der erste Lkw kommt nach 4 Minuten an (Frist 4: 1 Lkw), der Umweg trägt erst ab Frist 7: dann kommen 6 Lkw an. Bei Frist 10 sind es 15; statisch (3 mal 10 = 30) wäre es das Doppelte.",
    "⏱️ Frühankunft": "Der beste Plan für Minute 3 schickt 5 Lkw je Minute über S - A - B - T (5 Lkw kommen bis Minute 3 an). Für Frist 8 ist es besser, diesen Weg zurückzunehmen: der Plan aus S - A - T und S - B - T (je 4 Minuten) liefert 75 Lkw statt 55 ohne Rücknahme, bringt aber bis Minute 3 keinen einzigen Lkw ans Gate. Der zeitwiederholte Fluss ist für jede Frist optimal, aber nicht für alle zugleich.",
    "🔗 Kette": "Drei Straßen hintereinander, je 2 Lkw je Minute und 3 Minuten: ein einziger Weg mit 9 Minuten. Bis Minute 8 kommt nichts an, bei Frist 12 sind es 8 Lkw (2 Lkw je Minute in 4 Wiederholungen); statisch (2 mal 12 = 24) wäre es das Dreifache. 100 Lkw brauchen 58 Minuten, genau die Untergrenze: ohne Umwege gibt es keine Lücke.",
    "⌛ Große Frist": "Dasselbe Netz mit Frist 60: 982 Lkw; statisch (19 mal 60 = 1 140) sind es nur noch 16 % zu viel, weil die Anlaufzeit im Verhältnis kleiner wird. Das Zeitnetz hat 856 Knoten und 2 950 Kanten, Dinic scannt darin 24 890 Kanten, das 35-fache des statischen Verfahrens (716, unverändert gegenüber Frist 20).",
    "⚡ Kleine Frist": "Frist 8 im selben Netz: der kürzeste Weg braucht 5 Minuten, es kommen nur 19 Lkw an. Statisch (19 mal 8 = 152) wäre es das Achtfache: kurze Fristen sind Anlaufzeit, und der statische Fluss sagt darüber nichts.",
    "🧪 Ohne Rücknahme": "Nur Vorwärtskanten: kürzeste Wege werden gefüllt, ohne je Fluss zurückzunehmen. Das Netz liefert dann 210 statt 222 Lkw (94,6 %): ein einmal belegter Weg wird nie freigegeben, auch wenn ein anderer Verlauf mehr bringt. Der Plan hat 12 Wege statt 11.",
}
