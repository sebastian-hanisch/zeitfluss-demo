# Fluss über die Zeit – wie viele Lkw kommen in T Minuten am Gate an, und braucht man dafür das ganze Zeitnetz? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-zeitfluss-demo.streamlit.app/)**

Fünfte Erweiterung (Stück 18, **E5 Fluss über die Zeit**) der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Kind von [ssp-demo](https://github.com/sebastian-hanisch/ssp-demo) (Kosten = Fahrzeit) und [dinic-demo](https://github.com/sebastian-hanisch/dinic-demo) (Max-Flow im Zeitnetz):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Konzept – den **zeitwiederholten Fluss** von Ford und Fulkerson (1958) – an einem wachsenden Beispiel.
Ein Terminal will wissen, wie viele Lkw innerhalb einer Frist von T Minuten am Gate ankommen können, wenn jede Straße nur eine bestimmte Zahl Lkw **je Minute** einfahren lässt und jede Fahrt ihre **Fahrzeit** dauert. Ein gewöhnlicher Max-Flow sieht die Zeit nicht.
Die naheliegende Antwort ist ein **zeitexpandiertes Netz** (jede Kreuzung ein Knoten je Minute, jede Straße eine Kante von Minute k nach k + Fahrzeit) mit einem Max-Flow darauf; das ist exakt, wächst aber mit der Frist. Ford und Fulkerson zeigten, dass man es nicht braucht: **ein statischer Fluss** auf dem kleinen Straßennetz mit der Fahrzeit als Kosten (Successive Shortest Paths), in Wege zerlegt und **in jeder Minute wiederholt**, liefert genau denselben Wert.
Diese Demo rechnet beides, vergleicht Größe und Aufwand – und zeigt die Grenze des Verfahrens: der Plan für eine Frist ist **für frühere Fristen nicht der beste**.

Anders als `leercontainer-demo` (Min-Cost-Flow im Zeit-Raum-Netz, Bestandsausgleich mit Vorschau-Fenster; dort sind Kapazitäten „nicht umgesetzt“) geht es hier um den **größten Fluss innerhalb einer Frist** mit Kapazität je Minute und Fahrzeit je Straße, und um die Frage, ob man das Zeitnetz überhaupt braucht; gemeinsam ist nur das Mittel der Zeitexpansion. Die Terminalkapazität am Gate (Abfertigung, Warteschlange) ist Sache von `gate-demo`.
Vehikel: ein Schichtennetz vom Sammelraum zum Gate (Kapazität 1 bis 6 Lkw je Minute, Fahrzeit 1 bis 5 Minuten), dazu vier feste Lehrnetze (Zwei Straßen, Engpass, Kette, Frühankunft).

**Einordnung in die Reihe (die Kanten des Graphen):** Kind von Successive Shortest Paths (Stück 6: Kosten = Fahrzeit, Rücknahmekanten) und Dinic (Stück 2: Gegenprobe im großen Netz); Stück 1 und 2 liefern den statischen Fluss, der hier zur Schranke wird. Bisher gebaut: die zwölf Stücke der Hauptlinie, die Erweiterungen E1 (drei Stücke), E4 (zwei Stücke) und dieses Stück.
```
edmonds-karp-demo → dinic-demo (Max-Flow, Zeitnetz-Gegenprobe)                          [gebaut]
ssp-demo (Kosten = Fahrzeit, Rücknahme) ─┐
                                          └─ zeitfluss-demo (Fluss über die Zeit)      [dieses Stück]
leercontainer-demo (Zeit-Raum-Netz, Min-Cost, Nachbar ohne Kante)                       [gebaut]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: Lehrnetze von Hand, Beispielnetze über ihre Seeds, Verteilungen über 40 feste Netze (Seeds ab 100000, dieselben wie in den Flussdemos; die Größenreihe über 5 Netze). Standard: 3 Schichten mit je 4 Kreuzungen (14 Knoten, 34 Straßen), Dichte 60 %, Seed 1, Frist 20 Minuten.
Alles ist ganzzahlig und deterministisch (eigener Zufallsstrom): Werte, Weg- und Kantenzahlen sind auf allen Plattformen dieselben; Aufwand zählt in gescannten Kanten, nie in Sekunden. Die Kopien aus den Vorgängern sind bewacht (`tests/test_copies.py`).

**Der Satz von Ford und Fulkerson gilt – in jedem Netz, das wir probiert haben.** Der zeitwiederholte Fluss liefert **222** Lkw bis Minute 20 (11 Wege, statischer Fluss 19 je Minute, kürzester Weg 5 Minuten); der Max-Flow im zeitexpandierten Netz (296 Knoten, 950 Kanten) ist ebenfalls 222, mit und ohne Warte-Kanten. Über **40 von 40** festen Netzen (Frist 20; ebenso bei Frist 10 und 40) stimmen beide Werte überein, ebenso in 60 weiteren Prüfungen im Test (30 Netze über mehrere Größen, je zwei Fristen; Absicherung gegen einen Off-by-one der Diskretisierung: T − ℓ + 1 Wiederholungen, nicht T − ℓ).
**Warten hilft nicht:** ohne die Warte-Kanten im Zeitnetz kommt derselbe Wert heraus (40 von 40); mit einer Ware und festen Kapazitäten gibt es nichts, wofür man warten müsste.

**Das große Netz ist nicht nötig – und teuer.** Das Zeitnetz hat T + 1 Knoten je Kreuzung (296 gegen 14 bei Frist 20; Mittel über 40 Netze 21,1-fach, dazu 28,4-fach die Kanten). Dinic darauf scannt im Standardnetz 7 090 Kanten, das statische Verfahren 716 (10-fach); über 40 Netze wächst das Aufwandsverhältnis mit der Frist: **10,0 / 37,9 / 91,2** bei Frist 10 / 20 / 40. Im Mittel über 5 feste Netze (Fristen 5 / 10 / 20 / 40 / 60): Knoten 86 / 156 / 296 / 576 / 856, Dinic 590 / 4 594 / 25 017 / 72 614 / 117 928 gescannte Kanten,
das statische Verfahren 125 / 415 / 483 / 483 / 483 – es hängt nicht mehr von der Frist ab, sobald alle Wege einbezogen sind. Frist 60 im Standardnetz: 982 Lkw, Zeitnetz mit 856 Knoten und 2 950 Kanten, Dinic 24 890 gegen 716 (35-fach).

**Statik führt in die Irre.** Wer die Fahrzeit ignoriert und den statischen Fluss mit der Frist multipliziert, überschätzt: im Standardnetz 19 mal 20 = 380 gegen 222 (**71 % zu viel**); über 40 Netze bei Frist 10 / 20 / 40 im Mittel das 3,3-fache / +51 % / +20 %. Selbst die Schranke f\*·(T − ℓ_min + 1), die den ersten Lkw erst nach der kürzesten Fahrzeit ankommen lässt, liegt im Mittel 77 % / 18 % / 7 % zu hoch. Bei Frist 8 im Standardnetz kommen nur 19 Lkw an, statisch wären es 152 (das Achtfache): kurze Fristen sind Anlaufzeit.
**Schnellste Ankunft.** 50 / 100 / 200 Lkw brauchen im Mittel über 40 Netze **10,5 / 13,8 / 20,8** Minuten, die Untergrenze aus dem statischen Fluss (⌈N / f\*⌉ + ℓ_min − 1) liegt bei 8,1 / 11,6 / 18,4: gut zwei Minuten Lücke, in keinem Netz gleich. Im Standardnetz: 14 Minuten für 100 Lkw (Untergrenze 10).

**Der Plan für eine Frist ist nicht für jede frühere Frist der beste.** Die Zerlegung des Endflusses enthält andere Wege als die frühen Runden des Verfahrens (Rücknahmen ändern Wege). Standardnetz, Plan für Frist 20: bei Frist 8 nur 14 von 19 Lkw (73,7 %), bei Frist 10 38 von 42 (90,5 %); der Verlust betrifft genau die Fristen 6 bis 13 (bei 13: 89 statt 90), ab 14 ist der Plan gleich dem besten.
Über 40 Netze (Frist 20): Minute 5 im Mittel **66,4 %** des dort besten Plans (schlechtestes Netz 0 %, 13 von 23 Netzen, in denen bis dahin ein Lkw ankommen kann, mit Verlust), Minute 10 **98,3 %** (schlechtestes 71,4 %, 11 von 40), Minute 15 kein Verlust in 40 von 40. Das Lehrnetz „Frühankunft“ zeigt es von Hand: der beste Plan für Minute 3 schickt 5 Lkw je Minute über S – A – B – T (5 Lkw bis Minute 3); für Frist 8 ist es besser, den Weg zurückzunehmen (S – A – T und S – B – T, je 4 Minuten): 75 statt 55 Lkw, aber bis Minute 3 kommt kein einziger an.
Ein **Frühankunftsfluss** (Gale 1959), der für alle Fristen zugleich optimal ist, existiert; er ist nicht gebaut (siehe Grenzen).

**Negativkontrolle Rücknahme.** Kürzeste Wege füllen, ohne je Fluss zurückzunehmen, bleibt im Standardnetz bei **210 statt 222** (94,6 %, 12 Wege); über 40 Netze (Frist 20) liegt es in **23 von 40** unter dem Optimum, im Mittel bei 98,1 %, schlimmstenfalls bei 87,1 %. Im Lehrnetz „Frühankunft“: 55 statt 75.
**Lehrnetze von Hand.** Zwei Straßen (1 je Minute / 2 min, 3 je Minute / 6 min): V(5) = 4, V(6) = 8, V(10) = 24 gegen 40 statisch; 100 Lkw nach 29 Minuten (Untergrenze 26). Engpass (Brücke 1 je Minute im Weg von 4 Minuten, Umweg 2 je Minute mit 7 Minuten): V(4) = 1, V(7) = 6, V(10) = 15 gegen 30 statisch. Kette (ein Weg, 9 Minuten, 2 je Minute): bis Minute 8 nichts, V(12) = 8 gegen 24 statisch, 100 Lkw nach 58 Minuten = Untergrenze (ohne Umwege keine Lücke).

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Bau standen sieben Vermutungen im Plan. Gemessen:

- **„Zeitwiederholter Fluss = Max-Flow im Zeitnetz“ – bestätigt** (40 von 40, dazu 60 weitere Netze und alle Lehrnetze für Fristen 1 bis 15).
- **„Das Zeitnetz ist um etwa den Faktor T größer“ – bestätigt für die Knoten (T + 1 je Kreuzung), für die Kanten etwas mehr (28,4-fach bei Frist 20), für den Aufwand nicht linear:** das Verhältnis wächst von 10 über 38 auf 91 (Frist 10 / 20 / 40), weil Dinic mit der Frist wächst und das statische Verfahren nach dem längsten Weg nicht mehr.
- **„Statik überschätzt“ – bestätigt, und stark bei kurzen Fristen** (das 3,3-fache bei Frist 10), schwach bei langen (+20 % bei Frist 40).
- **„Die Frühankunftslücke ist klein“ – nur teilweise.** Ein Vorab-Prototyp (12 Knoten, zufällige Netze) sah bei der halben Frist nur wenig Verlust, und auch auf dem Demo-Vehikel sind es bei der halben Frist im Mittel nur 1,8 % (Minute 10 bei Frist 20); bei einem Viertel der Frist aber **34 %** (Minute 5), im schlechtesten Netz 100 %. Der Verlust betrifft nur frühe Fristen und verschwindet nahe der Frist.
- **„Warten hilft nicht“ – bestätigt** (40 von 40, bei Frist 10, 20 und 40).
- **„Ohne Rücknahme deutlich schlechter“ – nur mäßig:** im Mittel 1,9 % unter dem Optimum, in 23 von 40 Netzen unter dem Optimum, schlimmstenfalls 12,9 %. Die Rücknahme ist nötig, aber selten ein großer Hebel auf zufälligen Schichtennetzen.
- **„Schnellste Ankunft = statische Untergrenze“ – widerlegt:** gut zwei Minuten darüber, in keinem der 40 Netze gleich; nur ohne Umwege (Kette) fallen beide zusammen.
- **Abweichung vom Plan:** das Lehrnetz „Frühankunft“ wurde nicht ausgedacht, sondern in kleinen Vier-Knoten-Netzen durch Zufallssuche gefunden (kleinstes mit fünf Straßen) und von Hand nachgerechnet; die Kapazitäten sind mit 5 multipliziert, damit der Verlust nicht 1 Lkw ist. Ein Frühankunftsfluss selbst ist nicht gebaut.

## Was die Demo zeigt

- **Lkw durchs Netz schicken:** Regler Frist T und Minute t (mit Abspielen), Karte mit der Einfahrtrate je Straße zur Minute t (Farbe = Auslastung), die Wege des Plans zum Hervorheben, Ankunftskurve gegen den besten Plan für jede frühere Frist.
- **Wie viel bringt die Zeit?** V(T) gegen die statischen Schranken, schnellste Ankunft von N Lkw gegen die Untergrenze.
- **Kompakt statt expandiert:** Wert im Zeitnetz (mit und ohne Warte-Kanten) gegen den zeitwiederholten Fluss, Größe und Aufwand.
- **Ist der Plan auch für frühere Fristen der beste?** Verhältnis A_T(θ) / V(θ).
- **Experimente (auf Abruf):** Größe und Aufwand je Frist, 40 feste Netze (Gleichheit, Schranken, Frühankunft, Negativkontrolle, schnellste Ankunft).
- **Wo die Annahmen enden:** eine Ware, feste Kapazitäten, ganze Minuten, kein Frühankunftsfluss, kein Warteraum am Gate, ein generiertes Netz.

## Modell und Verfahren

- **Straße:** Kapazität $c_e$ (Einfahrten je Minute), Fahrzeit $\tau_e$; Frist $T$; Einfahrt zu den Minuten $0,1,\dots$
- **Zeitexpandiertes Netz:** Knoten $(v,k)$, Kanten $(u,k)\to(v,k+\tau_e)$ mit Kapazität $c_e$, Warte-Kanten ohne Grenze; Max-Flow von allen $(s,k)$ nach allen $(t,k)$ (Dinic).
- **Zeitwiederholter Fluss:** statischer Fluss $x$ (Successive Shortest Paths, Kosten $\tau_e$, nur Wege mit $\ell\le T$), Wegezerlegung, jeder Weg $P$ fährt zu den Minuten $0,\dots,T-\ell_P$ mit $x_P$ los: $V(T)=\sum_P x_P(T-\ell_P+1)=(T+1)|x|-\sum_e\tau_e x_e$. Die Rundenlängen hängen nicht von $T$ ab: ein Lauf liefert $V(T)$ für jede Frist.
- **Frühankunft:** $A_T(\theta)=\sum_P x_P(\theta-\ell_P+1)^+\le V(\theta)$.

## Ehrliche Grenzen

- **Eine Ware, ein Ziel.** Bei mehreren Gütern oder Quellen mit begrenztem Angebot (schnellste Verlegung, „quickest transshipment“) ist der zeitwiederholte Fluss nicht mehr optimal (Hoppe und Tardos); nicht gebaut.
- **Zeitunabhängige Kapazitäten und Fahrzeiten.** Bei Sperrungen oder Schichtwechseln hilft Warten, und man braucht das Zeitnetz.
- **Ganze Minuten** (T − ℓ + 1 Wiederholungen); im stetigen Modell T − ℓ.
- **Kein Frühankunftsfluss** (Gale 1959, Minieka, Wilkinson): die Demo misst nur den Verlust des Plans für eine Frist bei früheren Fristen.
- **Kein Warteraum am Gate:** das Gate nimmt beliebig viele Lkw je Minute an.
- **Synthetische Daten:** ein Schichtennetz mit erzeugten Kapazitäten und Fahrzeiten, kein reales Straßennetz, keine Fremddaten.

## Bewusst nicht umgesetzt

- Frühankunftsfluss, Quickest Transshipment, zeitabhängige Kapazitäten, mehrere Güter, Terminalkapazität am Gate, stetige Zeit.

## Dateien

```
app.py                  Oberfläche (Streamlit)
zf_scenario.py          Schichtennetz, Lehrnetze, Zufallsgenerator
zf_ssp.py               Successive Shortest Paths (Kopie aus ssp-demo, mit max_length)
zf_dinic.py             Dinic (Kopie aus dinic-demo)
zf_edmonds_karp.py      Restgraph-Grundlagen (Kopie aus ssp-demo)
zf_dynamic.py           zeitwiederholter Fluss, Wegezerlegung, Kurven, Frühankunft, Negativkontrolle
zf_expanded.py          zeitexpandiertes Netz und Max-Flow darin
zf_evaluation.py        Analyse, Gegenprobe, Größe, Verteilungen, schnellste Ankunft
zf_visualization.py     Plotly-Abbildungen
zf_presets.py           Permalink, Presets, Zufalls-Seed
zf_constants.py         Konstanten, Regler-Grenzen, feste Seed-Mengen, Preset-Texte
tests/                  Kopien, Kern, Auswertung, Presets, Behauptungen, App, Regler-Zustand
```

## Lokal starten

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt
venv/Scripts/streamlit run app.py
```

## Tests ausführen

```bash
venv/Scripts/pip install -r requirements-dev.txt
venv/Scripts/python -m pytest tests/ -v
```

Gebaut mit Streamlit und Plotly; der Kern ist reines Python.
