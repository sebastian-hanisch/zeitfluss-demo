"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, beide Verfahren, Randgrößen, Zeit-Regler, Weg-Auswahl, ausgeblendete Regler, Permalink, Experimente auf Abruf."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import zf_constants as C
from zf_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


def _run(setup=None, timeout=300):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def _step_slider(at):
    found = [s for s in at.slider if s.key == "zf_step"]
    return found[0] if found else None


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info) + list(at.error)]


def test_default_renders_without_exception():
    at = _run()
    assert _metric(at, "Bis zur Frist T") == ["222"] and _metric(at, "Max-Flow im Zeitnetz") == ["222"] and _metric(at, "Statischer Fluss f* [je Min.]") == ["19"]
    assert _step_slider(at).value == 5 and _step_slider(at).max == 20
    assert any("Bis Minute 20 können 222 Lkw" in t for t in _texts(at))


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert not at.error and _metric(at, "Max-Flow im Zeitnetz")


@pytest.mark.parametrize("method", list(C.METHODS))
@pytest.mark.parametrize("net", list(C.NETS))
def test_every_method_and_net_renders(method, net):
    def setup(at):
        at.session_state["method_radio"] = method
        at.session_state["net_select"] = net
        at.session_state["deadline_slider"] = 12
    at = _run(setup)
    assert not at.error and _metric(at, "Max-Flow im Zeitnetz")


def test_extreme_sizes_render():
    for vals in ((("layers_slider", C.LAYERS_MIN), ("width_slider", C.WIDTH_MIN), ("density_slider", C.DENSITY_MIN), ("deadline_slider", C.T_MIN)),
                 (("layers_slider", C.LAYERS_MAX), ("width_slider", C.WIDTH_MAX), ("density_slider", C.DENSITY_MAX), ("deadline_slider", C.T_MAX))):
        def setup(at, vals=vals):
            for key, value in vals:
                at.session_state[key] = value
        at = _run(setup)
        assert not at.error and _metric(at, "Max-Flow im Zeitnetz")


def test_time_slider_moves_through_frames():
    at = _run()
    top = int(_step_slider(at).max)
    for value in (0, 1, top // 2, top):
        _step_slider(at).set_value(value)
        at.run()
        assert not at.exception and _step_slider(at).value == value


def test_path_selection_highlights_a_path():
    at = _run()
    box = next(s for s in at.selectbox if s.key == "zf_path")
    box.set_value(1)
    at.run()
    assert not at.exception and next(s for s in at.selectbox if s.key == "zf_path").value == 1


def test_early_lesson_shows_the_early_arrival_warning_and_text():
    at = _run(lambda a: _apply(a, C.PRESETS["⏱️ Frühankunft"]))
    assert any("Bei Frist 3 liefert der Plan für die Frist 8 nur 0 Lkw statt 5" in t for t in _texts(at))
    assert any("Frühankunft:" in m.value for m in at.markdown)


def test_naive_method_warns():
    at = _run(lambda a: _apply(a, C.PRESETS["🧪 Ohne Rücknahme"]))
    assert any("liefert der Plan 210 Lkw, der beste Plan 222" in t for t in _texts(at))


def test_hidden_controls_keep_their_values_across_a_net_switch():
    at = _run()
    at.sidebar.slider(key="layers_slider").set_value(4)
    at.run()
    at.sidebar.selectbox(key="net_select").set_value("chain")
    at.run()
    assert not at.exception and not [w for w in at.sidebar.slider if w.key == "layers_slider"]
    at.sidebar.selectbox(key="net_select").set_value("roads")
    at.run()
    assert at.sidebar.slider(key="layers_slider").value == 4 and not at.exception


def test_permalink_settings_are_loaded_and_clamped():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.query_params["net"] = "roads"
    at.query_params["layers"] = "99"
    at.query_params["density"] = "77"
    at.query_params["method"] = "naive"
    at.query_params["deadline"] = "1"
    at.query_params["trucks"] = "123"
    at.run()
    assert not at.exception
    assert at.sidebar.slider(key="layers_slider").value == C.LAYERS_MAX and at.sidebar.slider(key="density_slider").value == 80
    assert at.sidebar.radio(key="method_radio").value == "naive" and at.sidebar.slider(key="deadline_slider").value == C.T_MIN and at.sidebar.slider(key="trucks_slider").value == 120


def test_invalid_method_in_the_permalink_falls_back_to_the_default():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.query_params["method"] = "magic"
    at.run()
    assert not at.exception and at.sidebar.radio(key="method_radio").value == C.DEFAULT_METHOD


def test_experiments_run_on_demand(monkeypatch):
    import zf_evaluation as ev
    s_orig, d_orig, q_orig = ev.sizes, ev.distribution, ev.quickest_table
    monkeypatch.setattr(ev, "sizes", lambda params: s_orig(params, Ts=(5, 10), seeds=C.SIZE_SEEDS[:2]))
    monkeypatch.setattr(ev, "distribution", lambda params: d_orig(params, seeds=C.SWEEP_SEEDS[:3]))
    monkeypatch.setattr(ev, "quickest_table", lambda params: q_orig(params, ns=(30,), seeds=C.SWEEP_SEEDS[:3]))
    at = _run()
    for key in ("sizes_start", "dist_start"):
        next(b for b in at.button if b.key == key).click().run()
        assert not at.exception, key
    assert any(m.label == "Wert = Max-Flow im Zeitnetz" and m.value == "3 von 3" for m in at.metric)


def test_source_has_explicit_chart_keys_and_locked_axes():
    app = APP.read_text(encoding="utf-8")
    assert all(re.search(r"plotly_chart\(.*key=", line) for line in app.splitlines() if "st.plotly_chart(" in line)
    viz = (ROOT / "zf_visualization.py").read_text(encoding="utf-8")
    assert viz.count("return _base(fig") + viz.count("return _frame(fig") >= 6 and "def lock_axes" in viz
