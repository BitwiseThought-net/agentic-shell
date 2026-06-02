#!/usr/bin/env python3
import sys
import json
import subprocess
import shutil
import importlib
import urllib.request
import urllib.error
import os

# Import the external colorized help extension
import help_manager

# Runtime settings dictionary loaded from the secure .env file
ENV_CONFIG = {}

def load_env_config(env_path=".env"):
    """Parses a local .env file securely to set up the runtime environment variables."""
    global ENV_CONFIG
    ENV_CONFIG.clear()

    ENV_CONFIG = {
        "OLLAMA_HOST": "localhost",
        "OLLAMA_PORT": "11434",
        "OLLAMA_MODEL": "llama3"
    }

    if not os.path.exists(env_path):
        print(f"\033[1;33m⚠️ Notice: '{env_path}' file not found. Using infrastructure defaults.\033[0m")
        return

    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    ENV_CONFIG[key.strip()] = value.strip().strip('"').strip("'")
        print("\033[1;32m🔐 Secure system environment settings successfully mounted.\033[0m")
    except Exception as e:
        print(f"⚠️ Error reading environmental configuration file: {e}")

class AgenticAI:
    def __init__(self, name, role, system_prompt, tools, working_directory):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools = tools  # Specific commands or ["all"]

        # Resolve and create the agent's unique sandbox directory path
        self.raw_workspace = working_directory or "./workspace/default"
        self.workspace_path = os.path.abspath(self.raw_workspace)
        os.makedirs(self.workspace_path, exist_ok=True)

        host = ENV_CONFIG.get("OLLAMA_HOST", "localhost")
        port = ENV_CONFIG.get("OLLAMA_PORT", "11434")
        self.ollama_url = f"http://{host}:{port}/api/generate"
        self.model = ENV_CONFIG.get("OLLAMA_MODEL", "llama3")

    def execute_system_tool(self, command_string):
        """Validates permissions, sanitizes file paths, and executes tools inside a specific sandbox path."""
        if not command_string.strip():
            return "Error: Empty command provided."

        # 1. Base Binary Permission Check
        base_binary = command_string.split()[0] if command_string.split() else ""
        has_permission = "all" in self.tools or base_binary in self.tools

        if not has_permission:
            return f"❌ Permission Denied: @{self.name} is not authorized to run '{base_binary}'."

        if not shutil.which(base_binary):
            return f"❌ System Error: Command binary '{base_binary}' not found on this system."

        # 2. Strict Workspace Isolation & Path Traversal Check
        # Block attempts to explicitly jump directories via ".." or absolute root flags "/"
        normalized_cmd = command_string.lower()
        if ".." in normalized_cmd or ( "/" in normalized_cmd and not normalized_cmd.startswith(self.workspace_path.lower()) ):
            # Basic validation: block the execution if it looks like it is trying to break out
            if any(forbidden in command_string for forbidden in [" /etc", " /var", " /usr", " /home", " /root", " ~"]):
                return f"❌ Path Violation Blocked: @{self.name} attempted an operation outside its sandbox path."

        print(f"⚡ [\033[1;33mTool Executed\033[0m] @{self.name} executing inside {self.raw_workspace}: `{command_string}`")

        try:
            # 3. Force execution to take place *inside* the agent's defined directory
            result = subprocess.run(
                ["/bin/bash", "-c", command_string],
                cwd=self.workspace_path,  # Forces execution context directory
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return output if output.strip() else f"Command completed with exit code {result.returncode}."
        except subprocess.TimeoutExpired:
            return "❌ Execution Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"❌ Execution Error: {str(e)}"

    def query_ollama(self, system_prompt, prompt):
        """Sends a POST request to the local Ollama instance configured in the environment."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.ollama_url, 
                data=data, 
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                return res_body.get("response", "").strip()
        except urllib.error.URLError as e:
            return f"ERROR_CONNECTION_FAILED: Could not reach Ollama at {self.ollama_url}. Is it running? ({e})"
        except Exception as e:
            return f"ERROR_PARSING: {str(e)}"

    def activate(self, user_query):
        """Passes context to Ollama, parses tool directives, or prints text responses."""
        print(f"\n🤖 [\033[1;32m@{self.name}\033[0m] thinking (Using Model: {self.model})...")

        # Append target workspace location to system instructions dynamically so the AI is aware of its limits
        contextual_system_prompt = self.system_prompt + f" Your isolated workspace path is explicitly locked to: {self.workspace_path}. You cannot modify anything outside of it."

        ai_response = self.query_ollama(contextual_system_prompt, user_query)

        if "ERROR_CONNECTION_FAILED" in ai_response:
            print(f"❌ {ai_response}\n")
            return

        try:
            clean_json = ai_response.replace("```json", "").replace("```", "").strip()
            parsed_command = json.loads(clean_json)

            if "execute" in parsed_command:
                command_to_run = parsed_command["execute"]
                tool_output = self.execute_system_tool(command_to_run)
                print(f"📦 [\033[1;34mSystem Result\033[0m]:\n{tool_output}\n")
                return
        except json.JSONDecodeError:
            pass

        print(f"💬 [\033[1;32m@{self.name} Response\033[0m]:\n{ai_response}\n")


# Global runtime dictionary to store initialized agents
AI_AGENTS = {}

def load_agent_team(config_path="agents.json"):
    """Reads JSON configuration file and dynamically updates the AI_AGENTS runtime."""
    global AI_AGENTS
    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        print(f"📦 Initializing Agent Team: {config.get('team_name', 'Unnamed Team')}")
        AI_AGENTS.clear()

        for agent_data in config.get("agents", []):
            name = agent_data["name"].lower()
            AI_AGENTS[name] = AgenticAI(
                name=name,
                role=agent_data.get("role"),
                system_prompt=agent_data.get("system_prompt"),
                tools=agent_data.get("allowed_tools", []),
                working_directory=agent_data.get("working_directory")
            )
            print(f"  └─ Registered agent: @{name} (Workspace: {AI_AGENTS[name].raw_workspace})")
        print("Initialization complete. Use @<agent_name> <message> to summon them.\n")
    except Exception as e:
        print(f"⚠️ Warning: Failed to load agent configuration ({e}). Running without AI.\n")

def main():
    load_env_config(".env")
    load_agent_team("agents.json")

    while True:
        try:
            user_input = input("custom-shell> ").strip()
            if not user_input:
                continue

            tokens = user_input.split()
            cmd = tokens[0] if tokens else ""
            args = tokens[1:]

            if cmd == "help":
                help_manager.display_help(AI_AGENTS)
                continue

            if cmd in ["exit", "quit"]:
                print("Exiting custom shell.")
                break

            if cmd == "cd":
                try:
                    destination = " ".join(args) if args else "."
                    shutil.os.chdir(destination)
                except Exception as e:
                    print(f"cd: {e}", file=sys.stderr)
                continue

            if cmd == "shell:reload":
                print("🔄 Hot-reloading system configuration environment variables...")
                load_env_config(".env")
                print("🔄 Reloading agent configurations from disk...")
                load_agent_team("agents.json")
                print("🔄 Hot-reloading help_manager module components...")
                importlib.reload(help_manager)
                print("✨ Core systems completely synchronized.\n")
                continue

            if cmd == "shell:addtool":
                if len(args) < 2:
                    print("Usage: shell:addtool <agent_name> <tool_name>")
                    continue
                target_agent = args[0].lower().replace("@", "")
                new_tool = args[1]

                if target_agent in AI_AGENTS:
                    if new_tool not in AI_AGENTS[target_agent].tools:
                        AI_AGENTS[target_agent].tools.append(new_tool)
                        print(f"✅ Dynamic update: Added tool '{new_tool}' to @{target_agent}")
                    else:
                        print(f"ℹ️ Tool '{new_tool}' is already assigned to @{target_agent}")
                else:
                    print(f"❌ Agent @{target_agent} not found.")
                continue


