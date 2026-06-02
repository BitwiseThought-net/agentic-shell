#!/usr/bin/env python3
"""
Help Management Extension Module
Handles colorized rendering of system documentation.
"""

# Standard ANSI Terminal Color Sequences
CLR_RESET   = "\033[0m"
CLR_HEADER  = "\033[1;36m"  # Bold Cyan
CLR_SECTION = "\033[1;34m"  # Bold Blue
CLR_CMD     = "\033[1;32m"  # Bold Green
CLR_ARG     = "\033[33m"    # Yellow
CLR_TEXT    = "\033[37m"    # Light Gray
CLR_MUTED   = "\033[90m"    # Dark Gray

def display_help(active_agents=None):
    """Prints a beautifully colorized guide of all custom shell capabilities."""
    active_agents = active_agents or {}

    print("\n" + f"{CLR_HEADER}" + "="*65)
    print("  CUSTOM AGENTIC SHELL - INTERFACE HELP DECK")
    print("="*65 + f"{CLR_RESET}")

    print(f"\n{CLR_SECTION}📌 CORE SHELL OVERRIDES{CLR_RESET}")
    print(f"  {CLR_CMD}help{CLR_RESET}              - Displays this command reference breakdown.")
    print(f"  {CLR_CMD}cd {CLR_ARG}<path>{CLR_RESET}         - Updates the execution directory of the parent shell.")
    print(f"                      Example: {CLR_MUTED}cd /var/log{CLR_RESET}")
    print(f"  {CLR_CMD}exit / quit{CLR_RESET}       - Terminates the session and returns to native terminal.")

    print(f"\n{CLR_SECTION}🛠️  SYSTEM CONFIGURATION MANAGEMENT{CLR_RESET}")
    print(f"  {CLR_CMD}shell:reload{CLR_RESET}      - Re-parses JSON and hot-reloads the help system.")
    print(f"                      Example: {CLR_MUTED}shell:reload{CLR_RESET}")
    print(f"  {CLR_CMD}shell:addtool{CLR_RESET}     - Grants an execution binary target to a running agent.")
    print(f"                      Format:  {CLR_CMD}shell:addtool {CLR_ARG}<agent_name> <tool_name>{CLR_RESET}")
    print(f"                      Example: {CLR_MUTED}shell:addtool @git_guru docker{CLR_RESET}")

    print(f"\n{CLR_SECTION}🤖 ACTIVE AI AGENT ROUTING COMMANDS{CLR_RESET}")
    if active_agents:
        for name, agent in active_agents.items():
            print(f"  {CLR_CMD}@{name:<15}{CLR_RESET} - Role: {CLR_TEXT}{agent.role}{CLR_RESET}")
            print(f"                     Allowed Tools: {CLR_ARG}{agent.tools}{CLR_RESET}")
            print(f"                     Example: {CLR_MUTED}@{name} check status of my work{CLR_RESET}")
    else:
        print(f"  {CLR_MUTED}(No active agents running. Load via agents.json configuration){CLR_RESET}")

    print(f"\n{CLR_SECTION}💻 NATIVE LINUX FALL-THROUGH{CLR_RESET}")
    print(f"  {CLR_TEXT}* Any command not explicitly listed above is directly forwarded to Bash.{CLR_RESET}")
    print(f"    Example: {CLR_MUTED}ls -la | grep '.py'{CLR_RESET}")
    print(f"    Example: {CLR_MUTED}docker ps{CLR_RESET}")
    print(f"{CLR_HEADER}" + "="*65 + f"{CLR_RESET}\n")
