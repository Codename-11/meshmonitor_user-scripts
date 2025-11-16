# MeshMonitor User Scripts

A collection of community-contributed Auto Responder scripts for [MeshMonitor](https://meshmonitor.org) - a powerful web application for monitoring Meshtastic networks.

## About This Repository

This repository contains example user scripts that demonstrate how to create custom Auto Responder integrations for MeshMonitor. These scripts showcase various capabilities including:

- **Multi-Pattern Triggers**: Utilizing MeshMonitor's new multi-pattern trigger feature (see [PR #628](https://github.com/Yeraze/meshmonitor/pull/628))
- **API Integration**: Weather, geocoding, and AI services
- **Local Processing**: Trivia, facts, and command directory
- **Best Practices**: Error handling, message splitting, and proper JSON output

## Links

- **MeshMonitor Website**: https://meshmonitor.org
- **MeshMonitor GitHub**: https://github.com/Yeraze/meshmonitor/
- **Auto Responder Documentation**: See MeshMonitor docs for complete scripting guide

## Scripts Overview

### 🤖 AI Assistant (`ai.py`)

AI-powered assistant supporting local Ollama (offline) and cloud APIs (OpenAI, Anthropic).

**Features:**
- Offline AI support via Ollama
- Cloud AI support (OpenAI, Anthropic)
- Automatic fallback between providers
- Multi-pattern trigger support

**Example Triggers:**
- `ask, ask {question:.+}` - Ask AI questions
- `ai, ai {prompt:.+}` - Same as ask
- `chat, chat {message:.+}` - Same as ask

**Requirements:**
- Python 3.6+
- For Ollama: Ollama service running
- For OpenAI: `OPENAI_API_KEY` environment variable (optional)
- For Anthropic: `ANTHROPIC_API_KEY` environment variable (optional)

**Example Usage:**
```
ask what is mesh networking?
ai how do I improve range?
chat explain LoRa
ask (shows help)
```

---

### 🌤️ Weather Bot (`PirateWeather.py`)

Get weather information for any location using Pirate Weather API with OpenStreetMap geocoding.

**Features:**
- Free geocoding via Nominatim (OpenStreetMap)
- Pirate Weather API integration
- Supports any location format (city, zip, address, etc.)
- Multi-pattern trigger support

**Example Trigger:**
- `weather, weather {location:.+}` - Get weather for location

**Requirements:**
- Python 3.6+
- `PIRATE_WEATHER_API_KEY` environment variable (get free key from https://pirateweather.net/)

**Example Usage:**
```
weather 90210
weather "New York, NY"
weather Paris, France
weather (shows help)
```

---

### ☀️ Sunrise/Sunset Calculator (`sunrise.py`)

Calculate sunrise, sunset, and daylight times for any location using free APIs.

**Features:**
- Free sunrise-sunset.org API (no API key required)
- Free geocoding via Nominatim (OpenStreetMap)
- Automatic timezone detection
- Local time formatting
- Multi-pattern trigger support

**Example Triggers:**
- `sunrise, sunrise {location:.+}` - Get sunrise/sunset times
- `sunset, sunset {location:.+}` - Same as sunrise
- `daylight, daylight {location:.+}` - Same as sunrise

**Requirements:**
- Python 3.6+
- No API keys required (uses free services)

**Example Usage:**
```
sunrise 90210
sunset "New York, NY"
daylight Paris, France
sunrise (shows help)
```

---

### 🎲 Fun Bot (`fun.py`)

Entertainment bot providing trivia, facts, jokes, and quotes - all content stored locally.

**Features:**
- No external dependencies
- Daily variety (seeded by date)
- Mesh/radio/tech themed content
- Multiple command support

**Example Triggers:**
- `trivia` - Random trivia question
- `fact` - Interesting tech fact
- `joke` - Get a joke
- `quote` - Inspirational quote

**Requirements:**
- Python 3.6+
- No external dependencies or API keys required

**Example Usage:**
```
trivia
fact
joke
quote
```

---

### 📋 Commands Directory (`commands.py`)

Lists all available Auto Responder commands/triggers configured in your MeshMonitor instance.

**Features:**
- Dynamic command listing
- Multi-message support for long lists
- Easy to update when adding new scripts
- Multi-pattern trigger support

**Example Trigger:**
- `commands, command` - List all available commands

**Requirements:**
- Python 3.6+
- No external dependencies or API keys required

**Example Usage:**
```
commands
command
```

**Note:** This script does NOT respond to "help" as that is reserved for emergency services in Meshtastic. Use "commands" or "command" instead.

---

## Getting Started

### Prerequisites

- MeshMonitor instance running (see [MeshMonitor docs](https://meshmonitor.org) for setup)
- Python 3.6+ (scripts run in MeshMonitor's container)
- Docker Compose (for local development/testing)

### Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/meshmonitor_user-scripts.git
   cd meshmonitor_user-scripts
   ```

2. **Copy scripts to your MeshMonitor scripts directory:**
   ```bash
   # If using Docker Compose with volume mapping
   cp *.py /path/to/meshmonitor/scripts/
   chmod +x /path/to/meshmonitor/scripts/*.py
   ```

3. **Set up environment variables** (if needed):
   ```bash
   # Add to your docker-compose.yaml or .env file
   PIRATE_WEATHER_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here  # Optional
   ANTHROPIC_API_KEY=your_key_here  # Optional
   AI_PROVIDER=ollama  # or "openai" or "anthropic"
   ```

4. **Configure triggers in MeshMonitor:**
   - Navigate to Settings → Automation → Auto Responder
   - Click "Add Trigger"
   - Enter trigger pattern (see examples above)
   - Select "Script" as response type
   - Enter script path: `/data/scripts/YourScript.py`
   - Save trigger

### Testing Scripts Locally

You can test scripts locally before deploying:

```bash
# Test weather script
TEST_MODE=true PARAM_location="New York" PIRATE_WEATHER_API_KEY=your_key python3 PirateWeather.py

# Test AI script
TEST_MODE=true PARAM_question="What is mesh?" python3 ai.py

# Test fun script
TEST_MODE=true PARAM_command="trivia" python3 fun.py
```

## Multi-Pattern Triggers

MeshMonitor supports multi-pattern triggers (introduced in [PR #628](https://github.com/Yeraze/meshmonitor/pull/628)), allowing one trigger to match multiple message formats.

### Example

Instead of creating separate triggers:
- `weather` (for help)
- `weather {location}` (for queries)

You can use a single multi-pattern trigger:
- `weather, weather {location}`

This matches both:
- `"weather"` → Shows help
- `"weather NYC"` → Processes location query

### Benefits

- **Simplified Configuration**: One trigger instead of multiple
- **Consistent Behavior**: Same script handles help and queries
- **Backward Compatible**: Still works with single-pattern triggers

## Script Requirements

All scripts in this repository follow MeshMonitor's Auto Responder script requirements:

- ✅ Located in `/data/scripts/` directory
- ✅ Executable (`chmod +x`)
- ✅ Output valid JSON to stdout
- ✅ Complete within 10 seconds (timeout)
- ✅ Proper error handling
- ✅ Message length limits (200 chars per message)
- ✅ Support for multi-message responses

### Output Format

**Single Response:**
```json
{
  "response": "Your response text here (max 200 chars)"
}
```

**Multiple Responses:**
```json
{
  "responses": [
    "First message (max 200 chars)",
    "Second message (max 200 chars)"
  ]
}
```

## Environment Variables

All scripts receive these environment variables from MeshMonitor:

- `MESSAGE`: Full message text received
- `FROM_NODE`: Sender's node number
- `PACKET_ID`: Message packet ID
- `TRIGGER`: The trigger pattern that matched
- `PARAM_*`: Extracted parameters from trigger pattern (e.g., `PARAM_location`, `PARAM_question`)

## Contributing

Contributions are welcome! When submitting a script:

1. **Follow the guidelines:**
   - Use multi-pattern triggers where appropriate
   - Include comprehensive docstrings
   - Add error handling
   - Test locally before submitting

2. **Provide documentation:**
   - Script name and description
   - Example triggers (with multi-pattern support)
   - Requirements (dependencies, API keys)
   - Usage examples

3. **Submit via:**
   - Pull request to this repository
   - Or add to main MeshMonitor repo's `examples/auto-responder-scripts/` directory

## License

Scripts in this repository are provided as-is for the MeshMonitor community. Individual scripts may have their own licensing terms - see script headers for details.

## Acknowledgments

- [MeshMonitor](https://meshmonitor.org) - The amazing platform that makes this possible
- [Meshtastic](https://meshtastic.org) - Open source mesh networking
- Community contributors - For creating and sharing these scripts

## Support

For issues, questions, or contributions:
- **MeshMonitor Issues**: https://github.com/Yeraze/meshmonitor/issues
- **This Repository**: Open an issue or pull request

---

**Made with ❤️ for the MeshMonitor community**

