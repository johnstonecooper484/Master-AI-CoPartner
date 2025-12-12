# MASTER_SPEC v2 – CORE SYSTEM

This file describes the **core runtime** of the Master AI Co‑Partner:
- Full folder tree (everything visible, nothing hidden)
- Where the brain, memory, voice, eyes, hands, and config live
- Single‑machine focused, but ready for multi‑machine & cloud modes later

---

## 1. Full Project Tree (Canonical Layout)

```text
AI-CoPartner/
│
├── .env                          # Environment variables (LOCAL_LLM, API keys, flags)
├── requirements.txt              # Python dependencies for dev/runtime
├── README.md                     # Top-level project description
├── LICENSE                       # License (to be chosen later)
│
├── config/                       # CONFIG, FLAGS, SECURITY, LOGGING SETUP
│   ├── __init__.py
│   ├── settings.py               # Modes, feature flags, defaults
│   ├── machine_profiles.yaml     # single_pc / multi_node / server profiles
│   ├── integrations.yaml         # Polly, other TTS/STT/LLM providers
│   ├── security.yaml             # permissions, safety rules
│   ├── logging.yaml              # logging formats & rotation settings
│   └── logs/                     # RUNTIME LOG OUTPUT
│       ├── .gitkeep
│       ├── ai_engine_*.log       # brain activity
│       ├── core_main_*.log       # main loop, mode changes
│       ├── voice_*.log           # STT/TTS, mic issues
│       └── task_engine_*.log     # future task planner / jobs
│
├── core/                         # MAIN RUNTIME / BRAIN / LOGIC
│   ├── __init__.py
│   ├── main.py                   # Entry point: starts event bus, ai_engine, IO, HUD hooks
│   ├── core_manager.py           # Orchestrates subsystems, startup/shutdown
│   ├── ai_engine.py              # Core reasoning brain (single logical brain)
│   ├── event_bus.py              # Pub/sub messaging between modules
│   ├── command_handler.py        # Handles text/voice commands, system actions
│   ├── intent_router.py          # "Think before you act" layer: routes intents & calls AI
│   ├── hotkeys.py                # F12, global shortcuts, mode toggles
│   ├── security_guard.py         # (Planned) safety checks before actions/commands
│   │
│   ├── memory/                   # MEMORY BRAIN (short, long, skills, RAM buffer)
│   │   ├── __init__.py
│   │   ├── memory_manager.py     # API to read/write/query all memory types
│   │   ├── memory_store.py       # (Optional) shared helpers / persistence logic
│   │   ├── short_term.json       # current session context (conversation buffer)
│   │   ├── long_term.json        # important long-term notes & facts
│   │   ├── skills_index.json     # index of known skills & metadata
│   │   └── ram_buffer.json       # “virtual RAM” scratch space / working thoughts
│   │
│   ├── skills/                   # SKILL LOGIC (CODE, not raw data)
│   │   ├── __init__.py
│   │   ├── skill_manager.py      # registers skills, picks which to apply
│   │   ├── coding.py             # coding / dev helper skills
│   │   ├── gaming.py             # in-game helper skills
│   │   ├── life_assistant.py     # reminders, planning, life admin
│   │   └── experimental/         # new or WIP skills
│   │       └── __init__.py
│   │
│   └── io/                       # EARS / EYES / HANDS / VOICE
│       ├── __init__.py
│       ├── listener.py           # High-level voice listener; wires F12 → STT
│       ├── vision.py             # (Planned) screen capture + OCR logic
│       ├── kinect_adapter.py     # (Planned) Kinect / camera integration
│       │
│       ├── controls/             # HANDS: MOUSE & KEYBOARD CONTROL
│       │   ├── __init__.py
│       │   ├── keyboard_mouse.py # Low-level mouse moves, clicks, typing
│       │   ├── macros.py         # Higher-level actions ("type note", "click button")
│       │   └── game_integration.py # (Planned) per-game control helpers
│       │
│       └── speech/               # VOICE: STT & TTS PIPELINE
│           ├── __init__.py
│           ├── stt_engine.py     # Faster-Whisper (tiny/base) STT engine
│           ├── tts_engine.py     # TTS selector, routes to local or Polly providers
│           ├── voice_service.py  # Glue: mic → STT → intent → AI → TTS → speaker
│           └── providers/        # Concrete TTS/STT provider backends
│               ├── __init__.py
│               ├── local_pyttsx3.py   # Offline TTS (primary)
│               ├── amazon_polly.py    # Online TTS fallback (optional)
│               └── other_provider_stub.py # Placeholder for a 3rd TTS provider
│
├── data/                         # WHAT SHE LEARNS FROM & STORES (DATA ONLY)
│   ├── memories/                 # Raw memory files (separate from core/memory code)
│   │   ├── pinned/               # user-pinned important items
│   │   ├── archive/              # archived / compacted older memories
│   │   └── scratchpad/           # temporary notes / transient info
│   │
│   ├── skills/                   # SKILL DATA (not Python code)
│   │   ├── coding/               # e.g., code snippets, style guides
│   │   ├── gaming/               # maps, boss notes, build guides
│   │   └── life_admin/           # routines, checklists, templates
│   │
│   └── toolbox/                  # Resource docs the AI can read/learn from
│       ├── docs/                 # general documentation, how-tos
│       ├── guides/               # step-by-step guides (e.g., workflows)
│       ├── reference/            # technical references, API docs
│       └── blueprints/           # high-level design docs used as "brain food"
│
├── ui/                           # HUD & SETUP UI
│   ├── __init__.py
│   ├── hud/                      # Main HUD (Control panel)
│   │   ├── __init__.py
│   │   ├── main_window.py        # main window / frame
│   │   └── components/           # UI widgets
│   │       ├── status_panel.py   # CPU/memory/mode/status display
│   │       ├── mode_switcher.py  # offline / hybrid / multi-machine toggles
│   │       ├── voice_controls.py # mic on/off, TTS test, STT status
│   │       ├── machine_link_panel.py # connect/disconnect other PCs
│   │       └── logs_viewer.py    # basic log viewing / error summary
│   │
│   └── setup_wizard/             # FIRST-RUN WIZARD
│       ├── __init__.py
│       ├── wizard.py             # controls wizard flow
│       └── steps/
│           ├── welcome.py
│           ├── mic_test.py
│           ├── speaker_test.py
│           ├── stt_tts_choice.py
│           ├── mode_choice.py    # single PC / multi-machine / hybrid
│           └── summary.py
│
├── installers/                   # PACKAGING / INSTALLATION SCRIPTS
│   ├── windows/
│   │   ├── build.bat             # build script for Windows
│   │   └── nsis_script.nsi       # example NSIS installer script
│   ├── scripts/
│   │   ├── prepare_env.py        # set up venv, install deps, sanity checks
│   │   └── collect_assets.py     # gather resources for packaging
│   └── packaging_notes.md        # notes, options, future installer plans
│
├── tests/                        # TESTS (UNIT + INTEGRATION)
│   ├── test_ai_engine.py
│   ├── test_memory.py
│   ├── test_speech.py
│   ├── test_controls.py
│   └── test_integration_flow.py
│
├── tmp/                          # TEMPORARY FILES (SAFE TO DELETE)
│   ├── audio/                    # raw testing audio if needed
│   ├── vision/                   # screenshots, OCR input
│   └── debug/                    # scratch debug output
│
└── docs/                         # DOCUMENTATION FILES ALREADY IN PROJECT
    ├── AI_CoPartner_Master_Blueprint.md
    ├── AI_COPARTNER_MASTER_CONTROL.txt
    ├── KINECT_CAMERA_INTEGRATION.md
    ├── PROJECT_NOTE.txt
    └── PROJECT_GITHUB_POINTER.txt
```

---

## 2. Mental Model Summary (so you don’t have to guess)

**Brain:**  
- `core/ai_engine.py` + `core/intent_router.py`

**Ears (hearing you):**  
- `core/io/listener.py`  
- `core/io/speech/stt_engine.py`

**Mouth (speaking to you):**  
- `core/io/speech/tts_engine.py`  
- `core/io/speech/providers/local_pyttsx3.py`  
- `core/io/speech/providers/amazon_polly.py`

**Eyes (seeing screen / future camera):**  
- `core/io/vision.py`  
- `core/io/kinect_adapter.py`

**Hands (mouse & keyboard):**  
- `core/io/controls/keyboard_mouse.py`  
- `core/io/controls/macros.py`

**Memory (short, long, skills, RAM buffer):**  
- `core/memory/memory_manager.py`  
- `core/memory/short_term.json`  
- `core/memory/long_term.json`  
- `core/memory/skills_index.json`  
- `core/memory/ram_buffer.json`  
- plus data mirrors in `data/memories` and `data/skills`

**Skills (what she’s good at):**  
- `core/skills/*` (code)  
- `data/skills/*` (supporting data)

**Config & security:**  
- `config/settings.py`  
- `config/machine_profiles.yaml`  
- `config/integrations.yaml`  
- `config/security.yaml`

**HUD / Control Panel:**  
- `ui/hud/*`  
- `ui/setup_wizard/*`

This is the **locked-in, canonical layout**.  
If we adjust it later, it will be an explicit version update, not a silent reshuffle.

---------------------------------------------------------------------------------------------------------------

🧠 2. Quick sanity map (so you don’t have to guess)

Just to anchor your brain:

Brain: core/ai_engine.py, core/intent_router.py

Ears: core/io/listener.py, core/io/speech/stt_engine.py

Mouth: core/io/speech/tts_engine.py + providers (pyttsx3 / Polly)

Eyes: core/io/vision.py, core/io/kinect_adapter.py

Hands: core/io/controls/keyboard_mouse.py, core/io/controls/macros.py

Memory: core/memory/* + data/memories/*

Skills: core/skills/* + data/skills/*

Toolbox / stuff she learns from: data/toolbox/*

HUD & setup: ui/hud/*, ui/setup_wizard/*

Security & config: config/*.py, config/*.yaml

This is now the canonical layout.
If we ever change it, we treat it like a version change, not a stealth rewrite.


---

## CORE FEATURE – System Device Awareness & Default IO Behavior

### Goal
The AI Co-Partner must always be aware of the basic hardware and I/O devices available on the system, so it can:

- Know what it can actually use (camera, microphone, speakers, keyboard, mouse, etc.)
- Communicate clearly with the user about what is connected
- Default safely to the system’s default input/output devices
- Help the user fix “I can’t hear you / you can’t hear me” situations

This is a **core requirement**, not an optional add-on.

---

### 1. Device Types to Detect

On startup, and when requested, the Co-Partner should detect and keep track of:

- **Audio Output Devices**
  - Desktop speakers
  - Headsets (USB, 3.5mm, Bluetooth)
  - Earbuds (Bluetooth, wireless)
- **Audio Input Devices**
  - Built-in microphones
  - Headset microphones
  - USB / XLR mics
  - Bluetooth hands-free mics
- **Cameras**
  - Built-in webcams
  - USB cameras
- **Input Devices**
  - Keyboards (wired, wireless, Bluetooth)
  - Mice (wired, wireless, Bluetooth)
  - Other pointing devices (trackpads, etc.)

The Co-Partner does not manage drivers; it only uses what the OS says is present.

---

### 2. Default Behavior

By default:

- The Co-Partner should:
  - Use the **system default output device** for speaking (TTS).
  - Use the **system default input device** for listening (voice/STT).

- On first run, or when a new session starts, it should:
  - Do a quick self-check:
    - “I am using [Output Device Name] to speak.”
    - “I am listening on [Input Device Name] for your voice.”
  - Optionally say:
    - “If you can’t hear me or I can’t hear you, ask me to list devices and we’ll switch.”

---

### 3. Device Listing & Selection (Core Logic)

When asked (voice or text), the Co-Partner should be able to:

1. **List devices** it sees, for example:

   - “For speakers/output, I see:
     - Desktop Speakers
     - USB Gaming Headset
     - Earbuds XYZ (Stereo)

     For microphones/input, I see:
     - USB Mic
     - Earbuds XYZ (Hands-Free)
     - Laptop Built-In Mic.”

2. **Offer to switch**:

   - “Which one do you want to use for my voice?”
   - “Which one do you want me to listen on as your microphone?”

3. **Apply the change** (where OS APIs allow):
   - Set new default input/output OR
   - Use that specific device just for the AI’s own audio IO.

---

### 4. “I Don’t Think You Can Hear Me” Logic

If the AI detects:

- No output device available  
- Or the selected device suddenly disappears  
- Or repeated failed responses from the user when voice is expected  

Then it should:

1. Say (via text and any available audio):
   - “I’m not sure you can hear me on the current device.”
2. Suggest:
   - “Ask me to list audio devices and we’ll pick a different one.”
3. Optionally fall back to:
   - System default speakers
   - Or another known-good device if available

---

### 5. Hotplug Awareness (New Devices Plugged In)

Whenever possible (depending on OS and APIs):

- If a **new audio device, camera, or input device** appears:
  - The Co-Partner should notice and log it.
  - Optionally say:
    - “I see a new device connected: [Device Name].  
       Do you want to use this for my voice, your mic, or camera?”

- If a device disappears:
  - Warn the user:
    - “The device I was using is no longer available. I’ll switch back to the system default.”

---

### 6. Safety & Stability

- The Co-Partner should:
  - Never rapidly switch devices without user intent.
  - Prefer stability over constant auto-changes.
  - Always explain:
    - What device it’s using now
    - What device it wants to switch to (if any)

- In case of confusion:
  - Default to:
    - System’s default speakers
    - System’s default mic
  - And clearly say what happened.

---
