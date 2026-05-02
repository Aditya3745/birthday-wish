# J.A.R.V.I.S. - Just A Rather Very Intelligent System

A fully autonomous, offline+online, self-evolving personal AI OS.

## Features

### Core Capabilities
- **Local LLM Brain**: Ollama (llama3/mistral) for offline operation
- **Online Fallback**: Groq → Gemini → Claude → OpenAI chain
- **Token Saver**: Intercepts simple queries locally
- **JARVIS Personality**: Calm, witty, loyal British AI assistant
- **Voice I/O**: pyttsx3 offline TTS, Whisper STT ready

### Multi-Agent Architecture
| Agent | Role |
|-------|------|
| Commander | Routes tasks to appropriate agents |
| Memory | SQLite + FAISS persistent storage |
| PC Control | Mouse, keyboard, window automation |
| Code | Write/run/debug code in any language |
| Security | Ethical hacking (authorized targets only) |
| Research | Web search and summarization |
| Scheduler | Reminders and cron jobs |
| Media | Music/video playback control |
| System Monitor | CPU/RAM/disk/battery stats |

## Installation

### 1. Install Dependencies
```bash
cd jarvis
pip install -r requirements.txt
```

### 2. Install Ollama (for offline LLM)
```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3.1
```

### 3. Set API Keys (optional, for online fallback)
```bash
export GROQ_API_KEY="your-key"
export GEMINI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

## Usage

### Start JARVIS
```bash
python main.py
```

### Example Commands
```
You: Hello
JARVIS: Greetings, sir. At your service.

You: What's my CPU usage?
JARVIS: [Shows system stats]

You: Write a Python function to calculate fibonacci
JARVIS: [Generates and can execute the code]

You: Open Chrome
JARVIS: Opening Chrome, sir.

You: Scan my network for vulnerabilities
JARVIS: [Performs authorized security scan]

You: Remember that I prefer coffee
JARVIS: I've made a note of that, sir.

You: Remind me to call John at 3pm
JARVIS: Reminder set for 3pm.
```

## Project Structure
```
jarvis/
├── main.py              # Entry point
├── core/
│   ├── brain.py         # LLM router (Ollama + online fallbacks)
│   ├── event_bus.py     # Async pub/sub system
│   ├── nlp_engine.py    # Intent classifier
│   └── voice.py         # TTS/STT handler
├── agents/
│   ├── commander.py     # Master task router
│   ├── memory_agent.py  # Persistent memory
│   ├── pc_control.py    # GUI automation
│   ├── code_agent.py    # Code generation/execution
│   ├── security_agent.py# Ethical hacking
│   ├── research_agent.py# Web search
│   ├── scheduler_agent.py# Reminders
│   ├── media_agent.py   # Media control
│   └── system_monitor.py# System stats
├── memory/              # SQLite databases + FAISS index
├── tools/               # Plugin tools
└── logs/                # System logs
```

## Architecture

### Event Bus
All agents communicate via async pub/sub event bus:
- No blocking calls
- Decoupled architecture
- Easy to add new agents

### Memory System
- **Episodic**: Conversations and events (SQLite)
- **Semantic**: Vector search on all knowledge (FAISS)
- **Personal**: User preferences (encrypted JSON)
- **Facts**: World knowledge (SQLite)
- **Skills**: Learned procedures (SQLite)

### Ethics Lock (Security Agent)
- Always asks: "Is this YOUR network/system?"
- Logs all security actions
- Refuses public IP scans without whitelist

## Offline First
- **Offline**: Ollama + local memory + pyttsx3
- **Online Detection**: Auto-detects connectivity
- **Sync**: Syncs when back online

## Customization

### Add New Agent
1. Create `agents/my_agent.py`
2. Inherit from base pattern
3. Register capabilities
4. Subscribe to event bus

### Change Personality
Edit `BrainConfig.system_prompt` in `core/brain.py`

### Add Online Provider
Implement `_call_provider()` method in `Brain` class

## License
MIT License - Build your own JARVIS!

---
*"Sometimes you gotta run before you can walk." - Tony Stark*
