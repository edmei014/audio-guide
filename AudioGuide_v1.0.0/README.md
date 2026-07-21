# Clear Audio

> Real-time AI Noise Reduction for Windows Playback and Microphone

Clear Audio is a Windows desktop application that removes background noise from both your system audio and microphone in real time using **DeepFilterNet**.

Unlike many audio tools, Clear Audio automatically configures the required Windows audio routing for playback. The user only selects the desired playback device and microphone — the application handles the VB-Audio Virtual Cable routing automatically.

---

# Screenshot

![Application](sources/application.png)

---

# How Clear Audio Works

![Description](sources/description.png)

### Playback (What You Hear)

When Playback Noise Reduction is enabled, Clear Audio automatically switches the Windows default playback device to **VB-Audio Virtual Cable**.

The processed audio is then sent directly to the output device selected inside Clear Audio.

The original Windows playback device is restored automatically when playback is disabled or when the application exits.

---

### Microphone (What You Send)

Clear Audio captures the selected microphone, removes background noise in real time and forwards the cleaned signal to **CABLE Output (VB-Audio Virtual Cable)**.

To use the processed microphone, simply select

**CABLE Output (VB-Audio Virtual Cable)**

as the microphone inside applications such as Discord, Microsoft Teams or Zoom.

The original Windows recording device is restored automatically when Clear Audio closes.

---

# Features

- Real-time AI noise reduction using DeepFilterNet
- Playback noise reduction
- Microphone noise reduction
- Automatic Windows playback routing
- Automatic restoration of Windows audio devices on exit
- Adjustable noise reduction strength
- Low-latency real-time processing

---

# Requirements

- Windows 10 / Windows 11
- Python 3.10 – 3.12
- VB-Audio Virtual Cable

---

# Installation

Clone the repository:

```powershell
git clone https://github.com/edmei014/audio-guide.git
cd audio-guide
```

Create a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Run the application:

```powershell
python main.py
```

---

# Technology

Clear Audio uses **DeepFilterNet**, an open-source deep learning model designed for real-time speech enhancement and background noise suppression with very low latency.

Audio processing is performed locally on the user's computer.

No audio leaves the device.

---

# License

MIT License
