"""Presets: vollständig, in den Grenzen, und jedes Beispiel zeigt, was sein Hilfetext behauptet."""

import pytest

import zf_constants as C
import zf_evaluation as ev
import zf_presets as P

KEYS = set(P.PRESET_KEYS)


def _params(p):
    return ev.Params(p["net"], p["layers"], p["width"], p["density"], p["method"], p["deadline"], p["trucks"], p["seed"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["method"] in C.METHODS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["density"] - C.DENSITY_MIN) % 10 == 0 and (p["trucks"] - C.TRUCKS_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_first_preset():
    assert _params(C.PRESETS["🚚 Straßennetz"]) == ev.DEFAULT_PARAMS


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🛣️ Zwei Straßen", "🚧 Engpass", "⏱️ Frühankunft", "🔗 Kette"}


def test_the_presets_show_both_good_and_bad_news():
    """Gut: jedes Beispiel hat einen Plan mit Lkw am Gate, und die Gegenprobe im Zeitnetz stimmt. Schlecht: die Negativkontrolle liegt unter dem Optimum, und im Frühankunfts-Beispiel liefert der Plan bei früher Frist nichts."""
    for name, p in C.PRESETS.items():
        a = ev.analyse(_params(p))
        assert a["plan"].value > 0 and ev.expanded(_params(p))["equal"], name
    assert ev.analyse(_params(C.PRESETS["🧪 Ohne Rücknahme"]))["plan"].value < ev.analyse(_params(C.PRESETS["🚚 Straßennetz"]))["plan"].value
    early = ev.analyse(_params(C.PRESETS["⏱️ Frühankunft"]))["early"]
    assert min(r[3] for r in early if r[3] is not None) == 0.0
