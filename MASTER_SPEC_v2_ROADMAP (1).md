# MASTER_SPEC v2 – ROADMAP & EXPANSION

This file describes the **future growth** of the Master AI Co-Partner:
- HUD / UI behavior
- Multi-machine / cluster options
- Cloud hybrid mode
- Installer / packaging plans
- Vision & screen understanding
- Memory/skills evolution
- Accessibility and safety
- Testing & release strategy

It **assumes** the canonical project tree defined in:
`MASTER_SPEC_v2_CORE.md`  
with the root layout:

- `config/` – flags, profiles, security, logging config
- `core/` – brain, memory, skills, IO (ears/eyes/hands/voice)
- `data/` – what she learns from (memories, skills data, toolbox)
- `ui/` – HUD & setup wizard
- `installers/` – packaging tools
- `tests/` – unit & integration tests
- `tmp/` – scratch
- `docs/` – design documents

---

## 1. HUD / UI System – Behavior & Goals

**Location:** `ui/hud/` and `ui/setup_wizard/`

### 1.1 HUD Main Window

Core responsibilities:
- Show **status**:
  - Online / offline / hybrid mode
  - Mic listening state
  - Local LLM status (connected / not found)
  - CPU / RAM usage summary
- Provide **controls**:
  - Big button: “Listen / Stop Listening”
  - Buttons for:
    - “Speak reply again”
    - “Pause speech”
    - “Clear short-term memory”
  - Mode selector:
    - `Offline`
    - `Hybrid`
    - `Multi-machine`

Planned modules:
- `ui/hud/main_window.py`
- `ui/hud/components/status_panel.py`
- `ui/hud/components/mode_switcher.py`
- `ui/hud/components/voice_controls.py`
- `ui/hud/components/machine_link_panel.py`
- `ui/hud/components/logs_viewer.py`

### 1.2 Settings Tabs

Inside HUD, add tabbed settings:

1. **General**
   - Start on boot (later)
   - Tray mode / visible window
   - Logging level (info / debug / quiet)

2. **Audio / Voice**
   - Input device selection (mic)
   - Output device selection (speakers/headset)
   - Test mic button
   - Test TTS button

3. **TTS Providers**
   - Local TTS enabled/disabled
   - Amazon Polly configuration
   - Placeholders for 2 future providers
   - Default provider selection per mode

4. **Machine Linking (Multi-machine)**
   - SCAN LAN for other nodes
   - Manual add by IP/hostname
   - Show connected worker machines

5. **Advanced**
   - Model paths (local LLM directory, etc.)
   - Developer experimental flags
   - Extra logging & diagnostics options

### 1.3 Setup Wizard

**Location:** `ui/setup_wizard/`

First-run goals:
- Prevent “blank screen, nothing works”
- Guide user through:
  1. Mic test (`mic_test.py`)
  2. Speaker test (`speaker_test.py`)
  3. STT/TTS preferences (`stt_tts_choice.py`)
  4. Mode selection:
     - Single PC only
     - Multi-machine ready
     - Cloud help allowed
  5. Summary page with “You’re ready” & suggested hotkeys

---

## 2. Multi-Machine & LAN Cluster Mode

**Key files:**
- `config/machine_profiles.yaml`
- `core/core_manager.py`
- `core/event_bus.py`
- `core/io/controls/*` (if remote control is allowed later)
- Future: `core/network/` (not yet in tree, to be added when built)

### 2.1 Goals

- Let advanced users spread load across multiple PCs:
  - STT on one machine
  - LLM on another
  - Vision/ OCR on another, if desired
- Normal users never *have* to use this.

### 2.2 Machine Profiles

In `config/machine_profiles.yaml`, define profiles like:

- `single_pc` – default
- `host_with_workers` – main brain + HUD + coordinates workers
- `worker_stt` – just runs STT and sends text back
- `worker_llm` – runs local LLM and returns responses

Later, add:
- `core/network/node_manager.py`
- `core/network/rpc_server.py`
- `core/network/rpc_client.py`

Traffic pattern (planned):

```text
local HUD → core_manager → network layer → worker node(s)
worker → sends results back → event_bus → ai_engine / io modules
```

---

## 3. Cloud Hybrid Mode (Optional)

This mode is **explicitly opt-in**.

**Config locations:**
- `config/integrations.yaml`
- `.env` (API keys)
- `core/ai_engine.py` (cloud fallback logic)

### 3.1 When Cloud is Used

Cloud help can be used only when:
- User has enabled “Hybrid mode” in HUD
- AND:
  - Local model is missing, OR
  - Local model is overloaded, OR
  - User explicitly says:
    - “Use online brain for this.”

Cloud is **never required** for basic operation.

### 3.2 Cloud Types

Possible cloud uses:
- LLM completion
- Extra STT / TTS options

But the design priority:
- **Offline-first**, with cloud as **bonus help**, not dependency.

---

## 4. Load Management & “Ask for Help” Behavior

**Key files:**
- `core/core_manager.py`
- `core/ai_engine.py`
- `config/settings.py`

### 4.1 System Monitoring

Future module (e.g., `core/system_monitor.py`) can:
- Watch CPU, GPU, RAM usage
- Watch queue length for:
  - STT requests
  - LLM responses
- Detect slowdowns / lag

### 4.2 Behavior

If thresholds are hit:

1. On **Single PC**:
   - Show HUD warning: “I’m starting to lag; consider pausing heavy tasks.”
   - Optionally:
     - Lower STT model size (base → tiny)
     - Reduce context length for LLM calls

2. If **Multi-machine enabled**:
   - Suggest offloading to worker nodes
   - Or automatically dispatch if user has allowed it

3. If **Cloud hybrid allowed**:
   - Ask: “Want me to send this bigger task to the online brain instead?”

User always stays in control.

---

## 5. TTS Provider System – Roadmap

**Key files:**
- `core/io/speech/tts_engine.py`
- `core/io/speech/providers/local_pyttsx3.py`
- `core/io/speech/providers/amazon_polly.py`
- `config/integrations.yaml`
- `ui/hud/components/voice_controls.py`
- `ui/hud/components/mode_switcher.py`
- `ui/hud/components/tts_settings_panel.py` (future)

### 5.1 Default Behavior

- **Primary**: local pyttsx3
- **Fallback**: Amazon Polly (if configured)
- **Future Providers**: at least 1–2 others, each in their own module

TTS selection rules:
- Per mode:
  - Offline-only mode: local only
  - Hybrid: local first, Polly for quality / specific voice
- Per request:
  - User may ask: “Use Polly Emma voice for this.”

---

## 6. Installer & Packaging Roadmap

**Key files:**
- `installers/windows/build.bat`
- `installers/windows/nsis_script.nsi`
- `installers/scripts/prepare_env.py`
- `installers/scripts/collect_assets.py`
- `config/settings.py`
- `README.md`

### 6.1 Goals

- Let a non-technical user:
  - Download installer
  - Run it
  - Complete setup wizard
  - Start talking to the AI in one session

### 6.2 Installer Steps (Planned)

1. Check for existing Python / or use embedded runtime
2. Create virtual environment
3. Install Python dependencies
4. Optionally:
   - Download or configure local LLM
   - Configure audio backends
5. Place shortcuts:
   - Desktop icon
   - Start menu
6. First launch:
   - Run setup wizard (HUD notifies when done)

---

## 7. Vision & Screen Understanding

**Key files:**
- `core/io/vision.py`
- `core/io/kinect_adapter.py`
- `data/toolbox/docs/` (for screen-reading prompts)
- `KINECT_CAMERA_INTEGRATION.md`

### 7.1 Screen-Only Phase

First stage (no camera yet):

- Capture screen region or full screen
- Run OCR on screenshot
- Let the AI:
  - Read text on the screen
  - Answer questions like:
    - “What window is open?”
    - “What error am I seeing?”
    - “What options do I have here?”

### 7.2 Camera/Kinect Phase

Second stage:

- For users who enable it:
  - Kinect or webcam integration
  - Basic object awareness:
    - “Is OBS open?”
    - “Which window is active?”
  - Optional only; never required.

All vision features:
- Must be clearly visible in HUD
- Must be easy to disable

---

## 8. Memory & Skills Evolution

**Key files:**
- `core/memory/*`
- `core/skills/*`
- `data/memories/*`
- `data/skills/*`
- `PROJECT_NOTE.txt` (for design intent)

### 8.1 Memory Behavior Goals

- Short-term:
  - Keep recent conversation context
  - Clearable with one command / HUD button
- Long-term:
  - Only store important facts
  - User can:
    - List memories
    - Edit/remove them
- RAM buffer:
  - Used for temporary planning by AI
  - Auto-cleaned periodically

### 8.2 Skills Growth

Examples:
- Coding skill:
  - Learns John’s project style and preferences
  - Stores patterns and snippets in `data/skills/coding/`
- Gaming skill:
  - Stores builds, boss patterns, FPS settings
- Life assistant:
  - Routines, checklists, planning templates

Future:
- “Skill training” mode where the AI:
  - Asks for examples
  - Builds new skill modules with user

---

## 9. Accessibility & UX

**Key files:**
- `ui/hud/components/*`
- `ui/setup_wizard/*`
- `config/settings.py`

Planned accessibility features:

- Large toggle buttons
- Minimal text where possible
- “Read this section aloud” button on:
  - Mode explanations
  - Settings descriptions
- Use dyslexia-friendly fonts & spacing where supported
- Clear step-by-step flows rather than complex pages

The project is designed to be:
- Navigable for users with memory and reading difficulties
- Comfortable for long-term use

---

## 10. Testing & Release Strategy

**Key files:**
- `tests/*`
- `config/settings.py`
- `PROJECT_NOTE.txt` (for priorities)

### 10.1 Test Types

- Unit tests:
  - `test_ai_engine.py`
  - `test_memory.py`
  - `test_speech.py`
  - `test_controls.py`
- Integration tests:
  - `test_integration_flow.py`
    - minimal full loop:
      - text → ai_engine → TTS
      - mock STT path

### 10.2 Release Milestones

Rough stage plan:

1. **Voice Core Stable**
   - STT + TTS loop
   - F12 hotkey
   - Local LLM integration
2. **Memory + Skills v1**
   - Short+long memory stable
   - At least one working skill path (coding/gaming)
3. **HUD + Setup Wizard**
   - User can configure everything via UI
4. **Installer**
   - Packaged build for Windows
5. **Multi-machine / Cloud Hybrid**
   - Optional advanced features
6. **Vision**
   - Screen reading support first
   - Optional camera later

Each stage:
- Adds tests
- Updates README / docs
- Updates specs if layout or responsibilities change

---

This ROADMAP file works together with:
- `MASTER_SPEC_v2_CORE.md`
- `AI_CoPartner_Master_Blueprint.md`
- `PROJECT_NOTE.txt`

to describe **what exists now** and **what we are building toward**, without losing any major component:
- brain
- memory
- voice
- eyes
- hands
- safety
- UI
- packaging
- future scaling
