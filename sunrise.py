#!/usr/bin/env python3
"""
Sunrise/Sunset calculator for MeshMonitor auto-responder.
Uses free sunrise-sunset.org API (no API key required).
Supports any location format using OpenStreetMap's free Nominatim geocoding service.

Requirements:
- Python 3.6+
- No API keys required (uses free services)

Setup:
1. Ensure volume mapping in docker-compose.yaml:
   - ./scripts:/data/scripts
2. Copy sunrise.py to scripts/ directory
3. Make executable: chmod +x scripts/sunrise.py
4. Copy to container: docker cp scripts/sunrise.py meshmonitor:/data/scripts/
5. Configure triggers in MeshMonitor web UI (using multi-pattern triggers):
   - Trigger: sunrise, sunrise {location:.+} (matches both "sunrise" for help and "sunrise {location}" for queries)
   - Trigger: sunset, sunset {location:.+} (matches both "sunset" for help and "sunset {location}" for queries)
   - Trigger: daylight, daylight {location:.+} (matches both "daylight" for help and "daylight {location}" for queries)
   - Alternative: {location:[\w\s,]+} (matches words, spaces, commas)
   - Response: /data/scripts/sunrise.py
   - Note: Multi-pattern triggers allow one trigger to handle both help and location queries

Usage:
- MeshMonitor auto-responder: sunrise {location} or sunset {location} or daylight {location}
- Local testing: TEST_MODE=true PARAM_location="City, State" python3 sunrise.py

Examples:
- sunrise "New York, NY"
- sunset 90210
- daylight "Paris, France"
- sunrise help

Made with ❤️ for the MeshMonitor community.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, date
from typing import Optional, Tuple, Dict, Any, List, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 fallback
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None

# Test mode flag - set to True for local testing
TEST_MODE = os.environ.get('TEST_MODE', 'false').lower() == 'true'

class SunriseBot:
    """Sunrise/Sunset bot that calculates daylight times using sunrise-sunset.org API."""

    def __init__(self):
        pass

    def geocode_location(self, location: str) -> Optional[Tuple[float, float]]:
        """
        Geocode a location using Nominatim (OpenStreetMap) geocoding service.
        This is a free service that doesn't require an API key.

        Args:
            location: Location string to geocode

        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        try:
            # Use OpenStreetMap's Nominatim geocoding service (free, no API key required)
            base_url = 'https://nominatim.openstreetmap.org/search'
            params = {
                'q': location,
                'format': 'json',
                'limit': 1
            }

            url = f'{base_url}?{urllib.parse.urlencode(params)}'

            # Add User-Agent header (required by Nominatim)
            headers = {
                'User-Agent': 'MeshMonitor-SunriseBot/1.0'
            }

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data and len(data) > 0:
                result = data[0]
                lat = float(result.get('lat'))
                lng = float(result.get('lon'))
                return (lat, lng)

        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                print(f'Geocoding rate limited for {location}, retrying in 1 second...', file=sys.stderr)
                time.sleep(1)
                return self.geocode_location(location)  # Retry once
            print(f'Geocoding HTTP error for {location}: {e.code}', file=sys.stderr)
        except Exception as e:
            # Log geocoding errors but don't fail completely
            print(f'Geocoding error for {location}: {str(e)}', file=sys.stderr)

        return None

    def get_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
        """
        Get latitude and longitude for a location using Nominatim geocoding.
        Supports any location format - relies entirely on OpenStreetMap's free geocoding service.

        Args:
            location: Any location string (city, zip, address, etc.)

        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        location = location.strip()

        if not location:
            return None

        # Try geocoding the location directly
        coords = self.geocode_location(location)
        if coords:
            return coords

        return None

    def get_timezone_name(self, lat: float, lng: float) -> str:
        """
        Get timezone name (e.g., "America/New_York") for a location.
        Tries API first, then falls back to TZ env var, then estimates from longitude.

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            Timezone name (IANA timezone), or None if unavailable
        """
        # Try timezone API first
        try:
            url = f'https://timeapi.io/api/TimeZone/coordinate?latitude={lat}&longitude={lng}'
            req = urllib.request.Request(url, headers={'User-Agent': 'MeshMonitor-SunriseBot/1.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                timezone_name = data.get('timeZone', None)
                if timezone_name:
                    return timezone_name
        except Exception:
            pass  # Fall through to other methods
        
        # Fall back to TZ environment variable (set in docker-compose)
        tz_env = os.environ.get('TZ', '').strip()
        if tz_env:
            return tz_env
        
        # Last resort: estimate from longitude (rough approximation)
        # US timezones: EST=-5, CST=-6, MST=-7, PST=-8
        # Each 15 degrees ≈ 1 hour, but US is roughly -75 to -125 longitude
        if -67 <= lng <= -125:  # Continental US
            if lng >= -67:  # Eastern
                return 'America/New_York'
            elif lng >= -87:  # Central
                return 'America/Chicago'
            elif lng >= -105:  # Mountain
                return 'America/Denver'
            else:  # Pacific
                return 'America/Los_Angeles'
        
        # For other locations, estimate from longitude
        # This is very rough but better than nothing
        estimated_offset = int(round(lng / 15))
        # Map common offsets to timezones (very rough)
        if estimated_offset == -5:
            return 'America/New_York'
        elif estimated_offset == -6:
            return 'America/Chicago'
        elif estimated_offset == -7:
            return 'America/Denver'
        elif estimated_offset == -8:
            return 'America/Los_Angeles'
        elif estimated_offset == 0:
            return 'UTC'
        
        return None

    def format_time(self, time_str: str, timezone_name: str = None) -> str:
        """
        Format time string from API (HH:MM:SS UTC) to local time (H:MM AM/PM).

        Args:
            time_str: Time string in format "HH:MM:SS" (UTC)
            timezone_name: IANA timezone name (e.g., "America/New_York") or None for UTC

        Returns:
            Formatted time string in local time
        """
        try:
            # Parse UTC time from API
            hour, minute, second = map(int, time_str.split(':'))
            
            # Create UTC datetime (using today's date)
            today = date.today()
            utc_dt = datetime(today.year, today.month, today.day, hour, minute, second)
            
            # Convert to local timezone if available
            if timezone_name and ZoneInfo:
                try:
                    tz = ZoneInfo(timezone_name)
                    local_dt = utc_dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(tz)
                    hour_local = local_dt.hour
                    minute = local_dt.minute
                except Exception:
                    # Fallback to UTC if timezone conversion fails
                    hour_local = hour
            else:
                # No timezone available, use UTC
                hour_local = hour
            
            # Convert to 12-hour format
            period = 'AM' if hour_local < 12 else 'PM'
            hour_12 = hour_local if hour_local <= 12 else hour_local - 12
            if hour_12 == 0:
                hour_12 = 12
            return f'{hour_12}:{minute:02d} {period}'
        except Exception:
            return time_str

    def get_sunrise_sunset(self, location: str) -> Dict[str, Any]:
        """
        Get sunrise and sunset times for a location.

        Args:
            location: Location string

        Returns:
            Dictionary with sunrise/sunset data or error message
        """
        try:
            coords = self.get_coordinates(location)
            if not coords:
                return {
                    'error': f'Could not find coordinates for location: {location}. '
                            'Try using a 5-digit zip code or "City, State" format.'
                }

            lat, lng = coords

            # Get timezone name for location (e.g., "America/New_York")
            timezone_name = self.get_timezone_name(lat, lng)

            # Build API URL (free, no API key required)
            url = f'https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&formatted=0'

            # Make API request
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data.get('status') != 'OK':
                return {'error': 'Sunrise-sunset API returned an error'}

            results = data.get('results', {})

            # Extract times (in UTC)
            sunrise_utc = results.get('sunrise', '')
            sunset_utc = results.get('sunset', '')
            day_length = results.get('day_length', 0)

            # Parse UTC times and convert to local time
            sunrise_utc_time = sunrise_utc.split('T')[1].split('+')[0]
            sunset_utc_time = sunset_utc.split('T')[1].split('+')[0]

            # Format times in local timezone (handles DST automatically)
            sunrise_formatted = self.format_time(sunrise_utc_time, timezone_name)
            sunset_formatted = self.format_time(sunset_utc_time, timezone_name)

            # Calculate day length in hours and minutes
            day_hours = int(day_length // 3600)
            day_minutes = int((day_length % 3600) // 60)

            # Format response (keep under 200 characters)
            response_text = (
                f'{location.title()}: Sunrise {sunrise_formatted} | '
                f'Sunset {sunset_formatted} | Day: {day_hours}h {day_minutes}m'
            )

            return {'response': response_text}

        except urllib.error.HTTPError as e:
            return {'error': f'Sunrise-sunset API error: {e.code} {e.reason}'}
        except urllib.error.URLError as e:
            return {'error': f'Network error: {e.reason}'}
        except json.JSONDecodeError:
            return {'error': 'Invalid response from sunrise-sunset API'}
        except Exception as e:
            return {'error': f'Unexpected error: {str(e)}'}

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
        """Return help text for the sunrise bot."""
        help_text = (
            'Sunrise/Sunset Bot:\n'
            '• sunrise {location} - Get times\n'
            '• sunset {location} - Same\n'
            '• daylight {location} - Same\n'
            'Examples:\n'
            '• sunrise 90210\n'
            '• sunset NYC\n'
            'See script for details.'
        )
        messages = self.split_message(help_text, max_chars=199)
        return messages[0] if len(messages) == 1 else messages

def main():
    """Main function to handle sunrise/sunset requests."""
    try:
        # Get location parameter from environment (set by MeshMonitor)
        location = os.environ.get('PARAM_location', '').strip()
        
        # If parameter is empty or seems incomplete, extract from MESSAGE using TRIGGER pattern
        # This handles cases where MeshMonitor doesn't extract multi-word parameters correctly
        if not location or (len(location) < 2 and ' ' in os.environ.get('MESSAGE', '')):
            original_message = os.environ.get('MESSAGE', '').strip()
            trigger_pattern = os.environ.get('TRIGGER', '').strip()
            
            if original_message and trigger_pattern:
                import re
                # Find {param} in trigger pattern (e.g., "sunrise {location}")
                param_match = re.search(r'\{(\w+)\}', trigger_pattern)
                if param_match:
                    # Get the trigger prefix (e.g., "sunrise " from "sunrise {location}")
                    trigger_prefix = trigger_pattern.split('{')[0].strip()
                    if original_message.lower().startswith(trigger_prefix.lower()):
                        # Extract everything after the trigger prefix
                        location = original_message[len(trigger_prefix):].strip()
                        # Remove quotes if present
                        if location.startswith('"') and location.endswith('"'):
                            location = location[1:-1]
                        elif location.startswith("'") and location.endswith("'"):
                            location = location[1:-1]

        bot = SunriseBot()

        if not location:
            # No location provided - show command-specific help
            response = (
                'Sunrise/Sunset requires a location.\n'
                'Usage:\n'
                '• sunrise {location} - Get times\n'
                '• sunset {location} - Same\n'
                '• daylight {location} - Same\n'
                'Examples:\n'
                '• sunrise 90210\n'
                '• sunset "New York, NY"'
            )
        elif location.lower() in ['help', 'h', '?']:
            # Explicit help request
            response = bot.get_help()
        else:
            # Get sunrise/sunset for location
            result = bot.get_sunrise_sunset(location)
            if 'error' in result:
                # Invalid location - provide helpful error with usage info
                error_msg = result["error"]
                response = (
                    f'Error: {error_msg}\n'
                    'Usage: sunrise {location}\n'
                    'Examples: sunrise 90210, sunset "NYC"'
                )
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

            print(f'Error in sunrise script: {str(e)}', file=sys.stderr)
        except:
            print('{"response": "Error: Script execution failed"}')
            sys.stdout.flush()
        finally:
            sys.exit(0)

if __name__ == '__main__':
    main()

