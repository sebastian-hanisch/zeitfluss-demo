"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (Standardmuster des Portfolios, siehe gm_presets.py in greedy-matching-demo)."""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import zf_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


def _choice(options):
    def cast(value):
        value = str(value)
        if value not in options:
            raise ValueError(value)
        return value
    return cast


def _choice_int(options):
    def cast(value):
        value = int(value)
        if value not in options:
            raise ValueError(value)
        return value
    return cast


SETTING_SPECS = {
    "net_select": SettingSpec("net", _choice(C.NETS), C.DEFAULT_NET),
    "method_radio": SettingSpec("method", _choice(C.METHODS), C.DEFAULT_METHOD),
    "deadline_slider": SettingSpec("deadline", int, C.DEFAULT_T, C.T_MIN, C.T_MAX),
    "trucks_slider": SettingSpec("trucks", int, C.DEFAULT_TRUCKS, C.TRUCKS_MIN, C.TRUCKS_MAX),
    "layers_slider": SettingSpec("layers", int, C.DEFAULT_LAYERS, C.LAYERS_MIN, C.LAYERS_MAX),
    "width_slider": SettingSpec("width", int, C.DEFAULT_WIDTH, C.WIDTH_MIN, C.WIDTH_MAX),
    "density_slider": SettingSpec("density", int, C.DEFAULT_DENSITY, C.DENSITY_MIN, C.DENSITY_MAX),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
}
PRESET_KEYS = {"net": "net_select", "method": "method_radio", "deadline": "deadline_slider", "trucks": "trucks_slider", "layers": "layers_slider", "width": "width_slider", "density": "density_slider", "seed": "seed_input"}
# Regler, die bei festen Lehrnetzen ausgeblendet sind: Streamlit löscht ihren Zustand, sobald sie nicht gezeichnet werden - der zuletzt gewählte Wert bleibt hier erhalten
KEPT = {key: f"_kept_{key}" for key in ("layers_slider", "width_slider", "density_slider", "seed_input")}
STEPS = {"density_slider": 10, "trucks_slider": 10}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in KEPT and state_key not in st.session_state:       # ausblendbare Regler: siehe seed_widget
            st.session_state[state_key] = spec.default


def seed_widget(state_key):
    """Vor dem Zeichnen eines ausblendbaren Reglers: fehlt sein Zustand, kommt der zuletzt gewählte (oder der Standard-) Wert.
    Ein Wert, der in einem Lauf ohne den Regler in den Zustand des Reglers geschrieben wird, erscheint später als Mindestwert im Regler, während die App mit dem geschriebenen Wert rechnet."""
    if state_key not in st.session_state:
        st.session_state[state_key] = st.session_state.get(KEPT[state_key], SETTING_SPECS[state_key].default)


def stash_kept_widget_state():
    """Permalink und Preset legen den Wert eines ausblendbaren Reglers nur in KEPT ab (der Regler holt ihn sich mit `seed_widget`, sobald er gezeichnet wird)."""
    for state_key, kept in KEPT.items():
        if state_key in st.session_state:
            st.session_state[kept] = st.session_state.pop(state_key)


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                st.session_state[state_key] = value
                if state_key in KEPT:
                    st.session_state[KEPT[state_key]] = value
            except (ValueError, TypeError):
                pass
    for key, step in STEPS.items():
        if key in st.session_state:
            lo = SETTING_SPECS[key].lo
            st.session_state[key] = int(lo + round((st.session_state[key] - lo) / step) * step)
    stash_kept_widget_state()
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][key]
        if state_key in KEPT:
            st.session_state[KEPT[state_key]] = C.PRESETS[name][key]
    stash_kept_widget_state()


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
