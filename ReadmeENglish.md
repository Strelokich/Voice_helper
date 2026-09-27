Local Voice Assistant

A desktop application with offline Russian speech recognition (via Vosk), a "phrase → action" command system, and the ability to connect to BionicGPT and any other neural network through an OpenAI-compatible API (OpenAI, Claude, or your own providers).

Open source and very simple — I'd be glad if someone wants to modify and improve it.

Features
 Offline Russian speech recognition via Vosk - runs entirely locally, with no internet connection and no cloud speech-recognition APIs involved (no Google/Yandex).
 Flexible command system: any phrase can be bound to an action (open an app/website, run a shell command, tell the time/date, control volume, etc.) through a convenient GUI, with no code changes.
 BionicGPT integration - a self-hosted neural network with an OpenAI-compatible API. Set the base_url of your instance, and voice requests ("ask bionic …") will go straight there.
 Third-party providers out of the box: OpenAI (ChatGPT), Anthropic (Claude), and any other OpenAI-compatible API (OpenRouter, LocalAI, LM Studio, Together AI, etc.) - all configured through the GUI, no code changes needed.
 Each provider is activated by its own voice phrase - you can keep several neural networks active at once and switch between them by voice.
 Responses are spoken aloud via pyttsx3 (offline TTS).
 PyQt6 interface: dark-purple neon theme, an animated listening indicator, and a detailed tabbed settings window.
Installation
Make sure Python 3.10+ is installed.
Install the dependencies:
bash
   pip install -r requirements.txt
Download the offline Vosk model for Russian:
Go to https://alphacephei.com/vosk/models
Download vosk-model-small-ru-0.22 (compact, ~45 MB, fine for everyday use) or vosk-model-ru-0.42 (larger, more accurate)
Unpack the archive into a models/ folder inside the project (or anywhere else)
On first launch, point to the unpacked folder in Settings → Recognition → Vosk model folder
(Linux only) Text-to-speech requires espeak-ng:
bash
   sudo apt install espeak-ng

On Windows and macOS, pyttsx3 uses the system voices (SAPI5 / NSSpeechSynthesizer) nothing extra to install, but for Russian speech on Windows a Russian voice package must be installed (Settings → Time & Language → Speech).

Running
bash
python main.py
Configuring commands

Open ⚙ Settings - Commands - Add. Specify:

Trigger phrase - e.g. "turn on the music"
Match type - the phrase must be contained in the recognized text (contains), match it exactly (exact), or be the start of it (startswith)
Action - one of the built-in ones: open_app, open_url, run_command, say_time, say_date, say_text, system_volume
Action parameters - e.g. for open_url specify url: https://youtube.com

New action types are easy to add programmatically — see actions/builtin_actions.py, the register_action(name, func) function.

Setting up BionicGPT and other neural networks

Open ⚙ Settings → Neural Networks → Add:

Field	What to enter
Type	bionicgpt for your BionicGPT instance, openai for OpenAI, anthropic for Claude, openai_compatible for any other OpenAI-compatible API
Base URL	The API address, e.g. http://localhost:3000/v1 for a local BionicGPT
API key	Access key (for BionicGPT it's created in its UI: Team Settings → API Keys)
Model	The name of the model configured on the provider's side
Trigger phrase	E.g. "ask bionic" — anything you say after this phrase is sent to the neural network

Click "Test connection" to make sure the provider responds before saving.

You can add as many providers as you like at the same time — the assistant will figure out which one a question is meant for based on the trigger phrase.

Project structure
voice_assistant/
├── main.py                    # entry point
├── config/
│   └── config_manager.py      # stores all settings in JSON
├── core/
│   ├── speech_recognizer.py   # Vosk (offline) + online engines
│   ├── tts.py                 # speech synthesis
│   ├── ai_providers.py        # BionicGPT / OpenAI / Anthropic / custom APIs
│   ├── command_engine.py      # matches phrases to commands and providers
│   └── assistant.py           # coordinator with no GUI dependencies
├── actions/
│   └── builtin_actions.py     # built-in actions for commands
└── ui/
    ├── theme.py                # dark-purple neon theme (QSS)
    ├── main_window.py          # main window
    ├── settings_window.py      # settings window (5 tabs)
    └── widgets/
        └── neon_orb.py          # animated state indicator
Known limitations
Vosk recognition is built for streaming speech from a microphone in real time; recognizing pre-recorded audio files would need a small amount of extra work (Vosk supports this too, it's just not wired up here).
system_volume on Windows uses the nircmd utility (needs to be downloaded separately and placed in PATH) — this is the most reliable way to control volume without extra Python libraries.
