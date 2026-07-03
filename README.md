# Audio Guide

**Echtzeit-Rauschunterdrückung für Windows** — bereinigt PC-Ton (Playback) und Mikrofon parallel mit [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet).

Version **1.0** ist eine schlanke Desktop-App mit einer einzigen Hauptansicht. Die modulare Audio-Architektur (Effect Chain, VST3-Host, getrennte Pipelines) bleibt im Code erhalten und ist für Version 2 unter `features/experimental/` vorbereitet.

## Was Audio Guide macht

- **Playback:** Rauschen aus dem Systemton entfernen (z. B. über VB-Cable)
- **Mikrofon:** Rauschen aus dem Mikrofon entfernen und auf ein virtuelles Ausgabegerät legen
- Beide Routen laufen **gleichzeitig** und unabhängig

## Voraussetzungen

- Windows 10/11
- Python **3.10–3.12** (DeepFilterNet)
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) (empfohlen für Playback-Routing)

## Installation

```powershell
git clone <repository-url>
cd "Audio Guide"
py -3.12 -m pip install -r requirements.txt
```

## Start

```powershell
py -3.12 main.py
```

## Bedienung

1. **Playback:** Eingang (z. B. „CABLE Output“) und Ausgang (Lautsprecher) wählen, Noise Reduction aktivieren, **Start**
2. **Mikrofon:** Mikrofon und virtuelles Ausgabegerät (z. B. „CABLE Input“) wählen, **Start**
3. Statusleiste zeigt Laufstatus, Latenz und CPU

Windows-Ausgabe auf **CABLE Input** routen, damit der Playback-Pfad den Systemton erhält.

## Projektstruktur

```
features/
  stable/                 # Version 1.0 (UI + NR-only-Konfiguration)
    config.py
    ui/main_window.py
    ui/route_panel.py
  experimental/           # Version 2+ (EQ, VST3, Plugin-UI)
    ui/tabbed_main_window.py
    ui/effect_chain_rack.py
    ...

audio/                    # Geräte, Capture, Output, Resampling, device_utils
effects/                  # Noise Reduction, EQ*, VST3-Host*
pipeline/                 # Effect Chain, Pipelines, Session
sources/                  # Playback- und Mikrofonquellen

* in v1.0 im UI ausgeblendet, Infrastruktur bleibt erhalten
```

## Test

```powershell
$env:PYTHONPATH = "$PWD"
py -3.12 scripts\test_pipeline.py
```

## Version 2 (experimentell)

Tab-UI mit EQ, VST3 und Plugin-Verwaltung:

```powershell
py -3.12 -m pip install -r requirements-experimental.txt
py -3.12 -c "from features.experimental.ui.tabbed_main_window import run; run()"
```

Siehe `features/experimental/README.md`.

## Lizenz

Siehe Repository-Lizenz.
