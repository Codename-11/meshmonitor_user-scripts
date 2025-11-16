#!/usr/bin/env python3
"""
Commands directory for MeshMonitor auto-responder.
Lists all available auto-responder commands/triggers.

Requirements:
- Python 3.6+
- No external dependencies or API keys required

Setup:
1. Ensure volume mapping in docker-compose.yaml:
   - ./scripts:/data/scripts
2. Copy commands.py to scripts/ directory
3. Make executable: chmod +x scripts/commands.py
4. Copy to container: docker cp scripts/commands.py meshmonitor:/data/scripts/
5. Configure trigger in MeshMonitor web UI (using multi-pattern trigger):
   - Trigger: commands, command (matches both "commands" and "command")
   - Response: /data/scripts/commands.py
6. To add custom commands, edit the COMMANDS dictionary in this script

Usage:
- MeshMonitor auto-responder: commands or command (NOT "help" - reserved for emergency)
- Local testing: TEST_MODE=true PARAM_command="commands" python3 commands.py

Examples:
- commands
- command

Note: This script does NOT respond to "help" as that is reserved for emergency services
in Meshtastic. Use "commands" or "command" instead.

Made with ❤️ for the MeshMonitor community.
"""

import os
import sys
import json
from typing import Dict, Any, List, Union

# Test mode flag - set to True for local testing
TEST_MODE = os.environ.get('TEST_MODE', 'false').lower() == 'true'

# Command registry - Easy to update when adding new scripts!
# Format: "trigger": {"desc": "Description", "example": "Example usage"}
COMMANDS = {
    "weather {location}": {
        "desc": "Get weather for location",
        "example": "weather 90210"
    },
    "sunrise {location}": {
        "desc": "Get sunrise/sunset times",
        "example": "sunrise NYC"
    },
    "sunset {location}": {
        "desc": "Get sunrise/sunset times",
        "example": "sunset NYC"
    },
    "daylight {location}": {
        "desc": "Get sunrise/sunset times",
        "example": "daylight NYC"
    },
    "trivia": {
        "desc": "Random trivia question",
        "example": "trivia"
    },
    "fact": {
        "desc": "Interesting tech fact",
        "example": "fact"
    },
    "joke": {
        "desc": "Get a joke",
        "example": "joke"
    },
    "quote": {
        "desc": "Inspirational quote",
        "example": "quote"
    },
    "ask {question}": {
        "desc": "AI assistant",
        "example": "ask what is mesh"
    },
    "ai {prompt}": {
        "desc": "AI assistant",
        "example": "ai explain LoRa"
    },
    "chat {message}": {
        "desc": "AI assistant",
        "example": "chat how to improve range"
    },
    "commands": {
        "desc": "List all commands",
        "example": "commands"
    },
    "command": {
        "desc": "List all commands",
        "example": "command"
    },
    # ADD YOUR CUSTOM COMMANDS HERE:
    # "mycommand {param}": {
    #     "desc": "Description of your command",
    #     "example": "mycommand example"
    # },
}

class CommandsBot:
    """Commands directory bot that lists all available commands."""

    def __init__(self):
        self.commands = COMMANDS

    def split_message(self, text: str, max_chars: int = 199) -> List[str]:
        """
        Split a long message into multiple messages, each under max_chars.

        Args:
            text: Text to split
            max_chars: Maximum characters per message (default: 199)

        Returns:
            List of message strings
        """
        if len(text) <= max_chars:
            return [text]

        messages = []
        lines = text.split('\n')
        current_message = []

        for line in lines:
            # Check if adding this line would exceed limit
            test_message = '\n'.join(current_message + [line])
            if len(test_message) <= max_chars:
                current_message.append(line)
            else:
                # Save current message and start new one
                if current_message:
                    messages.append('\n'.join(current_message))
                # If single line is too long, split it
                if len(line) > max_chars:
                    # Split long line by words
                    words = line.split(' ')
                    current_line = []
                    for word in words:
                        test_line = ' '.join(current_line + [word])
                        if len(test_line) <= max_chars:
                            current_line.append(word)
                        else:
                            if current_line:
                                messages.append(' '.join(current_line))
                            current_line = [word]
                    if current_line:
                        current_message = [' '.join(current_line)]
                else:
                    current_message = [line]

        # Add remaining message
        if current_message:
            messages.append('\n'.join(current_message))

        return messages

    def get_commands_list(self) -> Union[str, List[str]]:
        """
        Get formatted list of all commands.
        Returns array of messages if total exceeds 199 characters.

        Returns:
            Single string or list of strings (each <= 199 chars)
        """
        # Build full command list (without header)
        command_lines = []
        for trigger, info in self.commands.items():
            # Skip the commands/command entries themselves
            if trigger in ['commands', 'command']:
                continue
            command_lines.append(f"• {trigger} - {info['desc']}")

        # Build full text of just commands (no header yet)
        commands_text = '\n'.join(command_lines)

        # Split commands into multiple messages if needed
        # Reserve space for header line: "Available Commands: Page X of Y (Msg X/Y)\n"
        # Longest header: "Available Commands: Page 99 of 99 (Msg 99/99)\n" = ~50 chars
        max_chars_for_commands = 199 - 50  # Reserve 50 chars for header
        messages = self.split_message(commands_text, max_chars=max_chars_for_commands)

        # Add header with page info to each message
        if len(messages) > 1:
            numbered_messages = []
            for i, msg in enumerate(messages, 1):
                # Create header line: "Available Commands: Page X of Y (Msg X/Y)"
                header = f"Available Commands: Page {i} of {len(messages)} (Msg {i}/{len(messages)})"
                # Combine header and message
                full_msg = f"{header}\n{msg}"
                # Final safety check - split again if needed
                if len(full_msg) > 199:
                    # Re-split this message
                    split_msg = self.split_message(full_msg, max_chars=199)
                    numbered_messages.extend(split_msg)
                else:
                    numbered_messages.append(full_msg)
            return numbered_messages
        else:
            # Single message - just add header without page numbers
            return f"Available Commands:\n{messages[0]}" if messages else "No commands available."

    def get_help(self) -> str:
        """Return help text for the commands bot."""
        return (
            'Commands Bot:\n'
            '• commands - List commands\n'
            '• command - Same\n'
            'Note: Use "commands" not "help"\n'
            'See script to add custom commands.'
        )

def main():
    """Main function to handle commands requests."""
    try:
        # Get command parameter from environment (set by MeshMonitor)
        command = os.environ.get('PARAM_command', '').strip().lower()

        bot = CommandsBot()

        # If trigger is "commands" or "command" with no parameter, list all commands
        # If parameter is explicitly "help", show help text
        # Otherwise, if parameter exists but isn't recognized, show help
        if command in ['help', 'h', '?']:
            # Explicit help request
            response = bot.get_help()
        elif not command or command in ['commands', 'command']:
            # No parameter or parameter is "commands"/"command" - list all commands
            # This handles trigger "commands" with no {command} parameter
            response = bot.get_commands_list()
        else:
            # Unknown parameter, show help
            response = bot.get_help()

        # Ensure we always have a response
        if not response:
            response = 'Error: No response generated'

        # Output JSON response for MeshMonitor
        # If response is a list, use 'responses' field; otherwise use 'response'
        try:
            if isinstance(response, list):
                output = {'responses': response}
            else:
                output = {'response': response}
            print(json.dumps(output))
            sys.stdout.flush()

            if TEST_MODE:
                print(f'\n--- TEST MODE OUTPUT ---\n{response}\n--- END TEST ---\n', file=sys.stderr)
        except Exception as output_error:
            try:
                error_output = {'response': f'Error: Failed to format response: {str(output_error)}'}
                print(json.dumps(error_output))
                sys.stdout.flush()
            except:
                print('{"response": "Error: Script execution failed"}')
                sys.stdout.flush()

    except Exception as e:
        # Handle any unexpected errors - ensure we always output something
        try:
            error_msg = f'Error: {str(e)}'
            if len(error_msg) > 195:
                error_msg = error_msg[:192] + '...'
            output = {'response': error_msg}
            print(json.dumps(output))
            sys.stdout.flush()

            if TEST_MODE:
                print(f'\n--- TEST MODE ERROR ---\n{error_msg}\n--- END TEST ---\n', file=sys.stderr)

            print(f'Error in commands script: {str(e)}', file=sys.stderr)
        except:
            print('{"response": "Error: Script execution failed"}')
            sys.stdout.flush()
        finally:
            sys.exit(0)

if __name__ == '__main__':
    main()

