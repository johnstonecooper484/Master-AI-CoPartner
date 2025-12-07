# AI Co-Partner Master Blueprint
Version 1.0
Author: John + AI Co-Partner

---

## Purpose
This file defines the top-level architecture, behavior, and long-term design rules for the AI Co-Partner system.  
All development must follow this blueprint to maintain consistency across modules, machines, and future expansions.

---

## High-Level Architecture

### Core Machines (Three-Brain System)
1. **Primary Machine (Main PC):**
   - Core reasoning engine
   - Memory manager
   - Event bus
   - Safety and guardrails
   - STT/TTS pipeline
   - Realtime interaction

2. **Secondary Machine (ThinkStation A):**
   - Vision processing
   - Object detection
   - Camera + Kinect integration
   - Spatial awareness

3. **Tertiary Machine (ThinkStation B):**
   - Tool-use engine
   - Code generator
   - Heavy model inference
   - Autonomous task execution

---

## Major Subsystems

### 1. Core
- `main.py` – orchestration loop
- `core_manager.py` – subsystem lifecycle control
- `ai_engine.py` – reasoning + LLM interface
- `event_bus.py` – async event routing
- `logger/` – structured Rolling logs

### 2. Memory Layer
- Ephemeral short-term memory
- Long-term semantic memory
- Knowledge injection pipeline
- Full contextual awareness across machines

### 3. Skills System
Each skill is modular and registered automatically.
Examples:
- File management
- Coding assistance
- System control
- Vision analysis
- Audio understanding

### 4. IO Layer
Handles:
- Speech input
- Speech output
- Hotkeys
- UI hooks
- Websocket bridges

### 5. Security Layer
- Input sanitizing
- Injection detection
- Permission gating
- Sandbox execution rules

---

## Interaction Model

### Goals:
- Respond in real-time
- Maintain personality consistency
- Stay aware of prior instructions
- Grow its internal knowledge safely
- Self-improve within constraints

### Triggers:
- Voice triggers
- File system events
- Hotkeys
- Schedules
- External APIs

---

## Future UI System
Planned features:
- Realtime dashboard
- Memory browser
- Event router visualizer
- Camera feed + annotation
- Task builder interface

---

## Development Rules
1. Write safe, modular code.
2. Document all new files briefly.
3. Use logging everywhere.
4. Keep all configs in `/config`.
5. Do not hardcode secrets.
6. Maintain cross-machine compatibility.
7. Build in small units, test often.

---

# END OF BLUEPRINT
