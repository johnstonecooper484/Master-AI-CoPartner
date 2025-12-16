# Spec Add-On: Topic Knowledge Vaults + Reasoning & Logic Layer (v1)

This document extends the Master AI Co-Partner plan with:
1) **Topic Knowledge Vaults** (game/project/device folders)
2) A **Reasoning & Logic Layer** (engineer/designer brain style)
3) A clean path to **stop depending on LM Studio** (optional), by swapping the local inference backend.

---

## 1) Topic Knowledge Vaults (Game / Project / Device)

### Goal
When John starts a new “focus topic” (a game, a build project, a device, an invention idea), the Co-Partner creates a dedicated folder that becomes the single home for:
- gameplay observations and tips
- internet research summaries (with sources)
- build/settings/loadouts/parts lists
- your notes (voice or typed)
- optional screenshots/vision notes (only when allowed)

### Folder layout
`data/topics/<category>/<topic_slug>/`

Examples:
- `data/topics/games/once_human/`
- `data/topics/projects/dog_treat_launcher/`
- `data/topics/devices/arduino_uno_q/`

Inside:
```
data/topics/<category>/<topic_slug>/
  topic.json                 # metadata + status
  notes/
    john_notes.md            # human-readable notes
    session_log.jsonl        # append-only timestamped notes
  research/
    web_findings.jsonl       # summary + sources per search
  builds/
    settings.json            # configs / keybinds / tuning
    loadouts.json            # builds or parts lists
  memory/
    facts.jsonl              # durable “useful forever”
    patterns.jsonl           # strategies / recurring solutions
  media/
    screenshots/             # optional
    clips/                   # optional
```

### Creation triggers
A topic vault is created when:
- John says: “Start a new game study: <game>”
- John says: “Start a build project: <thing>”
- OR the AI proposes it and John approves.

### Memory rule
Most topic-specific info stays inside the topic vault to prevent global memory bloat.

---

## 2) Reasoning & Logic Layer (Engineer/Designer Brain)

### Important note (realistic expectation)
You cannot “extract” the model’s hidden chain-of-thought. The safe way is to implement:
- **A structured reasoning process** the app runs around the model (planner/checker)
- **Rules + constraints** the model must follow
- **Visible reasoning artifacts**: plans, checklists, tradeoffs, logs (not private thoughts)

This gives you an “engineer brain” feel without needing the model to reveal internal thinking.

### What we’re adding
A new module: **Reasoning Loop** (Plan → Act → Check → Save)

#### A) Plan (short, readable)
- Identify goal
- Identify constraints (time, safety, resources, “don’t touch without permission”)
- Choose one approach
- Output: a short plan (3–7 steps)

#### B) Act (safe, gated)
- Only allowed actions can run (allowlist)
- Anything risky or external asks for permission
- Output: action result, errors, next step

#### C) Check (think twice)
- Validate output against rules:
  - did we follow the mode rules?
  - did we avoid unsafe actions?
  - does the answer match the user’s request?
- Output: pass/fail + fix suggestion

#### D) Save (memory + topic vault)
- Write the “useful bits” into:
  - topic vault (most of it)
  - global memory only if it’s truly permanent

### “Engineer mindset” tuning knobs
Add a config profile:
- **style.engineer_mode = true**
- When enabled, responses should:
  - be structured
  - include tradeoffs (if relevant)
  - prefer durable designs, modular code, strong logging
  - avoid fluff unless asked

### Reasoning artifacts (visible outputs)
Instead of hidden thoughts, the AI produces:
- a **Plan**
- a **Decision record** (why this approach)
- a **Checklist** (what to verify)
- a **Next steps** block

These can be stored in:
- `data/topics/.../notes/session_log.jsonl`
- `data/topics/.../memory/patterns.jsonl`

---

## 3) Replacing LM Studio (Optional) with an Embedded Local Backend

### What you’re asking for
Right now, your app talks to a model that’s served by LM Studio (as a local API/server).
You want the model runtime to be “part of the program” instead of relying on LM Studio.

### Practical reality
Most local LLMs still run as:
- a local server (LM Studio / Ollama / vLLM), OR
- a library/runtime (llama.cpp bindings, etc.)

The *cleanest* architecture is:
- Keep your app the same
- Swap the backend using a **Provider Interface**
- Pick a backend later:
  - LM Studio (today)
  - Ollama (easy swap)
  - llama.cpp (more embedded)
  - vLLM (more performance, more setup)

### Design rule: Provider Interface
Create a single interface like:
- `LocalLLMProvider.generate(prompt, system, tools, config) -> text`
Then implement:
- `LMStudioProvider`
- `OllamaProvider`
- `LlamaCppProvider` (future)

Your Co-Partner logic never changes. Only the provider changes.

### Why this is worth it
- No rewrite later
- Clean testing (mock provider)
- Your reasoning layer stays identical

---

## 4) Files to add (planned)

### A) New spec docs
- `docs/TOPIC_KNOWLEDGE_VAULTS.md` (or keep this combined file)
- `docs/REASONING_AND_LOGIC_LAYER.md` (optional split)

### B) New code modules (future)
- `core/reasoning/reasoner.py`
- `core/reasoning/checkers.py`
- `core/llm/providers/base.py`
- `core/llm/providers/lmstudio.py`
- `core/llm/providers/ollama.py` (optional)

### C) Config additions
- `config/profiles/engineer.json`
- `config/profiles/gamer.json`

---

## 5) “Think twice before speaking” (simple implementation rule)
Before any reply is finalized:
1) **Mode check** (Game mode vs Normal mode)
2) **Safety check** (action gating)
3) **Clarity check** (short steps, no walls of text)
4) **Memory routing** (topic vault vs global)

---

## 6) Quick checklist (what this gives you)
- A folder-per-topic knowledge vault system
- A human-like workflow: plan, act, check, save
- A backend-agnostic local model system (LM Studio now, swap later)
- An “engineer brain” response style via profile flags

---

## Notes / Terms
- **Topic vault**: a per-topic folder under `data/topics/`
- **Reasoning artifacts**: plan/checklist/decision record saved as text or JSONL
- **Provider**: the module that talks to the local model runtime (LM Studio/Ollama/etc.)
