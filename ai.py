#!/usr/bin/env python3
"""
AI Assistant for MeshMonitor auto-responder.
Supports local Ollama (offline) and cloud APIs (OpenAI, Anthropic).

Requirements:
- Python 3.6+
- For Ollama: Ollama service running (see docker-compose.yaml)
- For OpenAI: OPENAI_API_KEY environment variable (optional)
- For Anthropic: ANTHROPIC_API_KEY environment variable (optional)

Setup:
1. Add Ollama service to docker-compose.yaml (see example in docker-compose.yaml)
2. Add AI environment variables to meshmonitor service:
   - AI_PROVIDER=ollama (or "openai" or "anthropic")
   - OLLAMA_MODEL=llama3.2:1b (optional, default shown)
   - OLLAMA_HOST=ollama (optional)
   - OLLAMA_PORT=11434 (optional)
   - OPENAI_API_KEY=your_key (optional, for OpenAI)
   - ANTHROPIC_API_KEY=your_key (optional, for Anthropic)
3. Ensure volume mapping in docker-compose.yaml:
   - ./scripts:/data/scripts
4. Copy ai.py to scripts/ directory
5. Make executable: chmod +x scripts/ai.py
6. Copy to container: docker cp scripts/ai.py meshmonitor:/data/scripts/
7. Start Ollama: docker-compose up -d ollama
8. Pull model: docker exec ollama ollama pull llama3.2:1b
9. Configure triggers in MeshMonitor web UI (using multi-pattern triggers):
   - Trigger: ask, ask {question:.+} (matches both "ask" for help and "ask {question}" for queries)
   - Trigger: ai, ai {prompt:.+} (matches both "ai" for help and "ai {prompt}" for queries)
   - Trigger: chat, chat {message:.+} (matches both "chat" for help and "chat {message}" for queries)
   - Response: /data/scripts/ai.py
   - Note: Multi-pattern triggers allow one trigger to handle both help and queries

Usage:
- MeshMonitor auto-responder: ask {question} or ai {prompt} or chat {message}
- Local testing: TEST_MODE=true PARAM_question="What is mesh?" python3 ai.py

Examples:
- ask "What is mesh networking?"
- ai "How do I improve range?"
- chat "Explain LoRa"
- ask (shows help)

Made with ❤️ for the MeshMonitor community.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List, Union

# Test mode flag - set to True for local testing
TEST_MODE = os.environ.get('TEST_MODE', 'false').lower() == 'true'

# Configuration
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'ollama').lower()
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2:1b')
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'ollama')
OLLAMA_PORT = os.environ.get('OLLAMA_PORT', '11434')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

class AIBot:
    """AI bot that queries local Ollama or cloud AI services."""

    def __init__(self):
        self.provider = AI_PROVIDER
        self.ollama_model = OLLAMA_MODEL
        self.ollama_url = f'http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate'
        self.openai_key = OPENAI_API_KEY
        self.anthropic_key = ANTHROPIC_API_KEY

    def query_ollama(self, prompt: str) -> Optional[str]:
        """
        Query local Ollama instance.

        Args:
            prompt: Question or prompt to send

        Returns:
            Response text or None if error
        """
        try:
            # Try Docker network first, then localhost
            urls = [
                f'http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate',
                'http://localhost:11434/api/generate'
            ]

            payload = {
                'model': self.ollama_model,
                'prompt': prompt,
                'stream': False
            }

            for url in urls:
                try:
                    data = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=30) as response:
                        result = json.loads(response.read().decode('utf-8'))
                        return result.get('response', '')
                except urllib.error.URLError:
                    continue  # Try next URL

            return None

        except Exception as e:
            print(f'Ollama query error: {str(e)}', file=sys.stderr)
            return None

    def query_openai(self, prompt: str) -> Optional[str]:
        """
        Query OpenAI API.

        Args:
            prompt: Question or prompt to send

        Returns:
            Response text or None if error
        """
        try:
            if not self.openai_key:
                return None

            url = 'https://api.openai.com/v1/chat/completions'
            payload = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 150  # Keep response short for mesh
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.openai_key}'
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('choices', [{}])[0].get('message', {}).get('content', '')

        except Exception as e:
            print(f'OpenAI query error: {str(e)}', file=sys.stderr)
            return None

    def query_anthropic(self, prompt: str) -> Optional[str]:
        """
        Query Anthropic Claude API.

        Args:
            prompt: Question or prompt to send

        Returns:
            Response text or None if error
        """
        try:
            if not self.anthropic_key:
                return None

            url = 'https://api.anthropic.com/v1/messages'
            payload = {
                'model': 'claude-3-haiku-20240307',
                'max_tokens': 150,  # Keep response short for mesh
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': self.anthropic_key,
                    'anthropic-version': '2023-06-01'
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('content', [{}])[0].get('text', '')

        except Exception as e:
            print(f'Anthropic query error: {str(e)}', file=sys.stderr)
            return None

    def get_ai_response(self, question: str) -> Dict[str, Any]:
        """
        Get AI response using configured provider with fallback chain.

        Args:
            question: Question or prompt

        Returns:
            Dictionary with response or error message
        """
        if not question or not question.strip():
            return {'error': 'Please provide a question or prompt.'}

        # Provider selection with fallback
        providers = []
        if self.provider == 'ollama':
            providers = ['ollama', 'openai', 'anthropic']
        elif self.provider == 'openai':
            providers = ['openai', 'ollama', 'anthropic']
        elif self.provider == 'anthropic':
            providers = ['anthropic', 'openai', 'ollama']
        else:
            providers = ['ollama', 'openai', 'anthropic']  # Default fallback

        response_text = None
        for provider in providers:
            if provider == 'ollama':
                response_text = self.query_ollama(question)
            elif provider == 'openai' and self.openai_key:
                response_text = self.query_openai(question)
            elif provider == 'anthropic' and self.anthropic_key:
                response_text = self.query_anthropic(question)

            if response_text:
                break

        if not response_text:
            return {
                'error': 'AI service unavailable. Check Ollama service or API keys.'
            }

        return {'response': response_text}

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
            test_message = '\n'.join(current_message + [line]) if current_message else line
            if len(test_message) <= max_chars:
                current_message.append(line)
            else:
                if current_message:
                    messages.append('\n'.join(current_message))
                if len(line) > max_chars:
                    words = line.split(' ')
                    current_line = []
                    for word in words:
                        test_line = ' '.join(current_line + [word]) if current_line else word
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

        if current_message:
            messages.append('\n'.join(current_message))

        return messages

    def get_help(self) -> Union[str, List[str]]:
        """Return help text for the AI bot."""
        help_text = (
            'AI Assistant:\n'
            '• ask {question} - Ask AI\n'
            '• ai {prompt} - Same\n'
            '• chat {message} - Same\n'
            'Examples:\n'
            '• ask "What is mesh?"\n'
            '• ai "How to improve range?"\n'
            'See script for more details.'
        )
        messages = self.split_message(help_text, max_chars=199)
        return messages[0] if len(messages) == 1 else messages

def main():
    """Main function to handle AI requests."""
    try:
        # Get question parameter from environment (set by MeshMonitor)
        # Parameter name depends on trigger: PARAM_question, PARAM_prompt, or PARAM_message
        question = (
            os.environ.get('PARAM_question', '') or
            os.environ.get('PARAM_prompt', '') or
            os.environ.get('PARAM_message', '')
        ).strip()
        
        # If parameter is empty or seems incomplete, extract from MESSAGE using TRIGGER pattern
        # This handles cases where MeshMonitor doesn't extract multi-word parameters correctly
        if not question or (len(question) < 3 and ' ' in os.environ.get('MESSAGE', '')):
            original_message = os.environ.get('MESSAGE', '').strip()
            trigger_pattern = os.environ.get('TRIGGER', '').strip()
            
            if original_message and trigger_pattern:
                # Extract parameter name from trigger pattern (e.g., "ask {question}" -> "question")
                # Then extract the actual value from MESSAGE
                import re
                # Find {param} in trigger pattern
                param_match = re.search(r'\{(\w+)\}', trigger_pattern)
                if param_match:
                    # Get the trigger prefix (e.g., "ask " from "ask {question}")
                    trigger_prefix = trigger_pattern.split('{')[0].strip()
                    if original_message.lower().startswith(trigger_prefix.lower()):
                        # Extract everything after the trigger prefix
                        question = original_message[len(trigger_prefix):].strip()
                        # Remove quotes if present
                        if question.startswith('"') and question.endswith('"'):
                            question = question[1:-1]
                        elif question.startswith("'") and question.endswith("'"):
                            question = question[1:-1]
                else:
                    # No parameter in trigger, try simple prefix matching
                    trigger_prefix = trigger_pattern.split('{')[0].strip() if '{' in trigger_pattern else trigger_pattern
                    if original_message.lower().startswith(trigger_prefix.lower()):
                        question = original_message[len(trigger_prefix):].strip()
                        if question.startswith('"') and question.endswith('"'):
                            question = question[1:-1]
                        elif question.startswith("'") and question.endswith("'"):
                            question = question[1:-1]
            elif original_message:
                # Fallback: try to extract question after "ask ", "ai ", or "chat "
                message_lower = original_message.lower()
                for prefix in ['ask ', 'ai ', 'chat ']:
                    if message_lower.startswith(prefix):
                        question = original_message[len(prefix):].strip()
                        # Remove quotes if present
                        if question.startswith('"') and question.endswith('"'):
                            question = question[1:-1]
                        elif question.startswith("'") and question.endswith("'"):
                            question = question[1:-1]
                        break

        bot = AIBot()

        if not question:
            # No parameter provided - show command-specific help
            response = (
                'AI Assistant requires a question.\n'
                'Usage:\n'
                '• ask {question} - Ask AI a question\n'
                '• ai {prompt} - Same as ask\n'
                '• chat {message} - Same as ask\n'
                'Examples:\n'
                '• ask "What is mesh?"\n'
                '• ai "How to improve range?"'
            )
        elif question.lower() in ['help', 'h', '?']:
            # Explicit help request
            response = bot.get_help()
        else:
            # Get AI response
            result = bot.get_ai_response(question)
            if 'error' in result:
                response = f'Error: {result["error"]}'
            else:
                response = result['response']
                # Split response if it exceeds 199 characters
                if isinstance(response, str) and len(response) > 199:
                    response = bot.split_message(response, max_chars=199)
                    if len(response) == 1:
                        response = response[0]

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
            sys.stdout.flush()  # Ensure output is flushed

            # In test mode, also print human-readable output
            if TEST_MODE:
                print(f'\n--- TEST MODE OUTPUT ---\n{response}\n--- END TEST ---\n', file=sys.stderr)

        except Exception as output_error:
            # If JSON output fails, try to output a simple error message
            try:
                error_output = {'response': f'Error: Failed to format response: {str(output_error)}'}
                print(json.dumps(error_output))
                sys.stdout.flush()
            except:
                # Last resort - output plain text error
                print('{"response": "Error: Script execution failed"}')
                sys.stdout.flush()

    except Exception as e:
        # Handle any unexpected errors - ensure we always output something
        try:
            error_msg = f'Error: {str(e)}'
            # Truncate if too long
            if len(error_msg) > 195:
                error_msg = error_msg[:192] + '...'
            output = {'response': error_msg}
            print(json.dumps(output))
            sys.stdout.flush()

            if TEST_MODE:
                print(f'\n--- TEST MODE ERROR ---\n{error_msg}\n--- END TEST ---\n', file=sys.stderr)

            # Log error to stderr for debugging
            print(f'Error in AI script: {str(e)}', file=sys.stderr)
        except:
            # Last resort - output plain text error
            print('{"response": "Error: Script execution failed"}')
            sys.stdout.flush()
        finally:
            sys.exit(0)  # Exit with 0 to ensure MeshMonitor processes the output

if __name__ == '__main__':
    main()

