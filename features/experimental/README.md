# Experimental UI (v2)

Tab-basierte Oberfläche mit Effekt-Racks, EQ-Presets und VST3-Plugin-Verwaltung.

## Aktivierung (Entwicklung)

```python
# main.py — für v2-Builds
from features.experimental.ui.tabbed_main_window import run
run()
```

## Module

| Modul | Beschreibung |
|-------|--------------|
| `ui/tabbed_main_window.py` | Drei-Tab-Hauptfenster |
| `ui/effect_chain_rack.py` | Effektkette + Parameter pro Route |
| `ui/plugins_tab.py` | VST3-Plugin-Bibliothek |
| `ui/playback_tab.py` | Playback-Tab (Legacy) |
| `ui/microphone_tab.py` | Mikrofon-Tab (Legacy) |

## Abhängigkeiten

Zusätzlich zu `requirements.txt`:

```
pip install -r requirements-experimental.txt
```

## Infrastruktur (unverändert in v1)

- `effects/vst_host.py` — Pedalboard VST3-Host
- `effects/equalizer.py` — 10-Band-EQ
- `pipeline/effect_chain.py` — konfigurierbare Kette
- `pipeline/audio_pipeline.py` — Echtzeit-Pipelines

Version 1.0 nutzt nur `features/stable/` und lässt diese Module inaktiv im UI.
