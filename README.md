# 🐚 Agentic Terminal Shell Wrapper

> Stop choosing between a static command line and isolated AI tools. This lightweight Linux shell wrapper seamlessly blends your native Bash ecosystem with local, autonomous Ollama agent teams-giving you secure, context-aware AI automation directly inside your terminal, bounded by real system permission engines you control.

---

## ✨ Features

* **Bash Fall-Through Engine:** Works just like your native terminal. Any standard command (`ls`, `cd`, `grep`, `docker`) bypasses the AI layer and executes directly in Bash.
* **Local Ollama Integration:** Zero dependencies on external cloud APIs or privacy-leaking networks. Runs fully localized inference on your machine.
* **Deterministic Sandbox Scoping:** Every agent is strictly containerized to a dedicated filesystem path defined in JSON, neutralizing path traversal or rogue execution behaviors.
* **Live System Hot-Reloading:** Modify your runtime infrastructure variables (`.env`), add tool permissions, or update agent behaviors (`agents.json`) and refresh them instantly mid-session with `shell:reload`.
* **Color-Coded Help Subsystem:** Fully externalized documentation module mapping custom commands dynamically without clogging main execution flows.

---

## 🏗️ Project Architecture

The workspace is cleanly decoupled into discrete configuration and modular execution boundaries:

```text
├── .env                  # Infrastructure connection configurations (Ignored by Git)
├── agents.json           # Agent persona declarations and sandbox boundaries
├── shell.py              # Main terminal loop, routing core, and permission logic
├── help_manager.py       # Dynamic, colorized documentation generator
└── workspace/            # Automatic directory containing isolated agent sandboxes
    ├── repo/             # Git Guru target execution workspace
    └── logs/             # Sys Admin target execution workspace
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have a local Ollama [instance]([https://ollama.com](https://github.com/BitwiseThought-net/the-architect)) running and the required model pulled to your machine:
```bash
ollama serve
ollama pull llama3
```

### 2. File Deployment
Clone or create the files in your directory and make the wrapper script entry point executable:
```bash
chmod +x shell.py
```

### 3. Environment Allocation (`.env`)
Create a secure `.env` file to handle connections separate from file execution logic:
```ini
# Ollama Local Service Configuration
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3
```

### 4. Agent Team Definitions (`agents.json`)
Configure your agent permissions and working sandboxes. The shell will automatically initialize these target directories if they do not exist.
```json
{
  "team_name": "Local Ollama DevOps Assistants",
  "agents": [
    {
      "name": "git_guru",
      "role": "Git version control assistant",
      "system_prompt": "You are a Git automation engineer. If you need to check state or run a command, reply ONLY with JSON format like this: {\"execute\": \"git status\"}. Do not add conversational text if you are executing a tool.",
      "allowed_tools": ["git"],
      "working_directory": "./workspace/repo"
    },
    {
      "name": "sys_admin",
      "role": "System diagnostics assistant",
      "system_prompt": "You are a Linux systems administrator. If you need to check resources, reply ONLY with JSON format like this: {\"execute\": \"df -h\"}.",
      "allowed_tools": ["df", "free", "uname"],
      "working_directory": "./workspace/logs"
    }
  ]
}
```

---

## 🚀 Usage Guide

To enter your newly created hybrid terminal workspace, run:
```bash
./shell.py
```

### 1. Running Standard Shell Commands
Standard inputs automatically fall through cleanly straight into native Bash:
```bash
custom-shell> ls -la | grep "shell"
custom-shell> mkdir testing_dir
```

### 2. Summoning Agents (`@` Routing Syntax)
To summon a specific AI agent instance and drop its execution into its designated sandbox pool, append its registered tag name:
```bash
custom-shell> @git_guru show me the status of this repository
```
*Behind the scenes:* The wrapper maps this to `git_guru`, queries Ollama using its localized system context, receives the `{ "execute": "git status" }` payload structure, validates path permissions, targets `./workspace/repo`, executes the binary, and prints your output return trace.

### 3. System Utility Control Overrides
The shell implements custom commands to allow you to configure system interactions dynamically:


| Command | Action | Example |
| :--- | :--- | :--- |
| `help` | Renders a color-coded, dynamic breakdown of active capabilities and agents. | `help` |
| `shell:reload` | Hot-reloads memory pointers, refreshes help systems, and updates `.env`/`agents.json` configurations without session loss. | `shell:reload` |
| `shell:addtool` | Inject an execution permission string dynamically into a running agent session. | `shell:addtool @git_guru docker` |
| `exit` / `quit` | Closes the custom wrapper runtime cleanly and returns control to native system terminals. | `exit` |

---

## 🛡️ Security Boundaries

* **Path Traversal Blocker:** If an LLM response attempts to breach containment using parent directory notation (`..`) or points to absolute critical systemic root systems (like `/etc`, `/var`, `/home`), the wrapper halts execution at the wrapper engine layer and registers a `Path Violation Blocked` protection prompt.
* **Whitelisted Command Enforcement:** Even if given `"all"` tool privileges, commands run strictly through a `shutil.which` verification wrapper check. If an agent tries to invoke a non-existent or restricted script environment command, it returns a safe exception trace rather than freezing terminal background pipelines.
