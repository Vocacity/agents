<!--BEGIN_BANNER_IMAGE-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/.github/banner_dark.png">
  <source media="(prefers-color-scheme: light)" srcset="/.github/banner_light.png">
  <img style="width:100%;" alt="The LiveKit icon, the name of the repository and some sample code in the background." src="https://raw.githubusercontent.com/livekit/agents/main/.github/banner_light.png">
</picture>

<!--END_BANNER_IMAGE-->
<br />

![PyPI - Version](https://img.shields.io/pypi/v/livekit-agents)
[![PyPI Downloads](https://static.pepy.tech/badge/livekit-agents/month)](https://pepy.tech/projects/livekit-agents)
[![Slack community](https://img.shields.io/endpoint?url=https%3A%2F%2Flivekit.io%2Fbadges%2Fslack)](https://livekit.io/join-slack)
[![Twitter Follow](https://img.shields.io/twitter/follow/livekit)](https://twitter.com/livekit)
[![Ask DeepWiki for understanding the codebase](https://deepwiki.com/badge.svg)](https://deepwiki.com/livekit/agents)
[![License](https://img.shields.io/github/license/livekit/livekit)](https://github.com/livekit/livekit/blob/master/LICENSE)

<br />

Looking for the JS/TS library? Check out [AgentsJS](https://github.com/livekit/agents-js)

## ✨ 1.0 release ✨

This README reflects the 1.0 release. For documentation on the previous 0.x release, see the [0.x branch](https://github.com/livekit/agents/tree/0.x)

## What is Agents?

<!--BEGIN_DESCRIPTION-->

The **Agents framework** enables you to build voice AI agents that can see, hear, and speak in realtime. It provides a fully open-source platform for creating server-side agentic applications.

<!--END_DESCRIPTION-->

## Features

- **Flexible integrations**: A comprehensive ecosystem to mix and match the right STT, LLM, TTS, and Realtime API to suit your use case.
- **Integrated job scheduling**: Built-in task scheduling and distribution with [dispatch APIs](https://docs.livekit.io/agents/build/dispatch/) to connect end users to agents.
- **Extensive WebRTC clients**: Build client applications using LiveKit's open-source SDK ecosystem, supporting nearly all major platforms.
- **Telephony integration**: Works seamlessly with LiveKit's [telephony stack](https://docs.livekit.io/sip/), allowing your agent to make calls to or receive calls from phones.
- **Exchange data with clients**: Use [RPCs](https://docs.livekit.io/home/client/data/rpc/) and other [Data APIs](https://docs.livekit.io/home/client/data/) to seamlessly exchange data with clients.
- **Semantic turn detection**: Uses a transformer model to detect when a user is done with their turn, helps to reduce interruptions.
- **MCP support**: Native support for MCP. Integrate tools provided by MCP servers with one loc.
- **Open-source**: Fully open-source, allowing you to run the entire stack on your own servers, including [LiveKit server](https://github.com/livekit/livekit), one of the most widely used WebRTC media servers.

## Installation

To install the core Agents library, along with plugins for popular model providers:

```bash
pip install "livekit-agents[openai,silero,deepgram,cartesia,turn-detector]~=1.0"
```

## Docs and guides

Documentation on the framework and how to use it can be found [here](https://docs.livekit.io/agents/)

## Core concepts

- Agent: An LLM-based application with defined instructions.
- AgentSession: A container for agents that manages interactions with end users.
- entrypoint: The starting point for an interactive session, similar to a request handler in a web server.
- Worker: The main process that coordinates job scheduling and launches agents for user sessions.

## Usage

### Simple voice agent

---

```python
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, elevenlabs, openai, silero

@function_tool
async def lookup_weather(
    context: RunContext,
    location: str,
):
    """Used to look up weather information."""

    return {"weather": "sunny", "temperature": 70}


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent = Agent(
        instructions="You are a friendly voice assistant built by LiveKit.",
        tools=[lookup_weather],
    )
    session = AgentSession(
        vad=silero.VAD.load(),
        # any combination of STT, LLM, TTS, or realtime API can be used
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
    )

    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(instructions="greet the user and ask about their day")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

You'll need the following environment variables for this example:

- DEEPGRAM_API_KEY
- OPENAI_API_KEY

### Multi-agent handoff

---

This code snippet is abbreviated. For the full example, see [multi_agent.py](examples/voice_agents/multi_agent.py)

```python
...
class IntroAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"You are a story teller. Your goal is to gather a few pieces of information from the user to make the story personalized and engaging."
            "Ask the user for their name and where they are from"
        )

    async def on_enter(self):
        self.session.generate_reply(instructions="greet the user and gather information")

    @function_tool
    async def information_gathered(
        self,
        context: RunContext,
        name: str,
        location: str,
    ):
        """Called when the user has provided the information needed to make the story personalized and engaging.

        Args:
            name: The name of the user
            location: The location of the user
        """

        context.userdata.name = name
        context.userdata.location = location

        story_agent = StoryAgent(name, location)
        return story_agent, "Let's start the story!"


class StoryAgent(Agent):
    def __init__(self, name: str, location: str) -> None:
        super().__init__(
            instructions=f"You are a storyteller. Use the user's information in order to make the story personalized."
            f"The user's name is {name}, from {location}"
            # override the default model, switching to Realtime API from standard LLMs
            llm=openai.realtime.RealtimeModel(voice="echo"),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    userdata = StoryData()
    session = AgentSession[StoryData](
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="echo"),
        userdata=userdata,
    )

    await session.start(
        agent=IntroAgent(),
        room=ctx.room,
    )
...
```

## Examples

<table>
<tr>
<td width="50%">
<h3>🎙️ Starter Agent</h3>
<p>A starter agent optimized for voice conversations.</p>
<p>
<a href="examples/voice_agents/basic_agent.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🔄 Multi-user push to talk</h3>
<p>Responds to multiple users in the room via push-to-talk.</p>
<p>
<a href="examples/voice_agents/push_to_talk.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🎵 Background audio</h3>
<p>Background ambient and thinking audio to improve realism.</p>
<p>
<a href="examples/voice_agents/background_audio.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🛠️ Dynamic tool creation</h3>
<p>Creating function tools dynamically.</p>
<p>
<a href="examples/voice_agents/dynamic_tool_creation.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>☎️ Outbound caller</h3>
<p>Agent that makes outbound phone calls</p>
<p>
<a href="https://github.com/livekit-examples/outbound-caller-python">Code</a>
</p>
</td>
<td width="50%">
<h3>📋 Structured output</h3>
<p>Using structured output from LLM to guide TTS tone.</p>
<p>
<a href="examples/voice_agents/structured_output.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🔌 MCP support</h3>
<p>Use tools from MCP servers</p>
<p>
<a href="examples/voice_agents/mcp">Code</a>
</p>
</td>
<td width="50%">
<h3>💬 Text-only agent</h3>
<p>Skip voice altogether and use the same code for text-only integrations</p>
<p>
<a href="examples/other/text_only.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>📝 Multi-user transcriber</h3>
<p>Produce transcriptions from all users in the room</p>
<p>
<a href="examples/other/transcription/multi-user-transcriber.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🎥 Video avatars</h3>
<p>Add an AI avatar with Tavus, Beyond Presence, and Bithuman</p>
<p>
<a href="examples/avatar_agents/">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🍽️ Restaurant ordering and reservations</h3>
<p>Full example of an agent that handles calls for a restaurant.</p>
<p>
<a href="examples/voice_agents/restaurant_agent.py">Code</a>
</p>
</td>
<td width="50%">
<h3>👁️ Gemini Live vision</h3>
<p>Full example (including iOS app) of Gemini Live agent that can see.</p>
<p>
<a href="https://github.com/livekit-examples/vision-demo">Code</a>
</p>
</td>
</tr>

</table>

## Running your agent

### Testing in terminal

```shell
python myagent.py console
```

Runs your agent in terminal mode, enabling local audio input and output for testing.
This mode doesn't require external servers or dependencies and is useful for quickly validating behavior.

### Developing with LiveKit clients

```shell
python myagent.py dev
```

Starts the agent server and enables hot reloading when files change. This mode allows each process to host multiple concurrent agents efficiently.

The agent connects to LiveKit Cloud or your self-hosted server. Set the following environment variables:
- LIVEKIT_URL
- LIVEKIT_API_KEY
- LIVEKIT_API_SECRET

You can connect using any LiveKit client SDK or telephony integration.
To get started quickly, try the [Agents Playground](https://agents-playground.livekit.io/).

### Running for production

```shell
python myagent.py start
```

Runs the agent with production-ready optimizations.

## Contributing

The Agents framework is under active development in a rapidly evolving field. We welcome and appreciate contributions of any kind, be it feedback, bugfixes, features, new plugins and tools, or better documentation. You can file issues under this repo, open a PR, or chat with us in LiveKit's [Slack community](https://livekit.io/join-slack).

<!--BEGIN_REPO_NAV-->

<br/><table>

<thead><tr><th colspan="2">LiveKit Ecosystem</th></tr></thead>
<tbody>
<tr><td>LiveKit SDKs</td><td><a href="https://github.com/livekit/client-sdk-js">Browser</a> · <a href="https://github.com/livekit/client-sdk-swift">iOS/macOS/visionOS</a> · <a href="https://github.com/livekit/client-sdk-android">Android</a> · <a href="https://github.com/livekit/client-sdk-flutter">Flutter</a> · <a href="https://github.com/livekit/client-sdk-react-native">React Native</a> · <a href="https://github.com/livekit/rust-sdks">Rust</a> · <a href="https://github.com/livekit/node-sdks">Node.js</a> · <a href="https://github.com/livekit/python-sdks">Python</a> · <a href="https://github.com/livekit/client-sdk-unity">Unity</a> · <a href="https://github.com/livekit/client-sdk-unity-web">Unity (WebGL)</a></td></tr><tr></tr>
<tr><td>Server APIs</td><td><a href="https://github.com/livekit/node-sdks">Node.js</a> · <a href="https://github.com/livekit/server-sdk-go">Golang</a> · <a href="https://github.com/livekit/server-sdk-ruby">Ruby</a> · <a href="https://github.com/livekit/server-sdk-kotlin">Java/Kotlin</a> · <a href="https://github.com/livekit/python-sdks">Python</a> · <a href="https://github.com/livekit/rust-sdks">Rust</a> · <a href="https://github.com/agence104/livekit-server-sdk-php">PHP (community)</a> · <a href="https://github.com/pabloFuente/livekit-server-sdk-dotnet">.NET (community)</a></td></tr><tr></tr>
<tr><td>UI Components</td><td><a href="https://github.com/livekit/components-js">React</a> · <a href="https://github.com/livekit/components-android">Android Compose</a> · <a href="https://github.com/livekit/components-swift">SwiftUI</a></td></tr><tr></tr>
<tr><td>Agents Frameworks</td><td><b>Python</b> · <a href="https://github.com/livekit/agents-js">Node.js</a> · <a href="https://github.com/livekit/agent-playground">Playground</a></td></tr><tr></tr>
<tr><td>Services</td><td><a href="https://github.com/livekit/livekit">LiveKit server</a> · <a href="https://github.com/livekit/egress">Egress</a> · <a href="https://github.com/livekit/ingress">Ingress</a> · <a href="https://github.com/livekit/sip">SIP</a></td></tr><tr></tr>
<tr><td>Resources</td><td><a href="https://docs.livekit.io">Docs</a> · <a href="https://github.com/livekit-examples">Example apps</a> · <a href="https://livekit.io/cloud">Cloud</a> · <a href="https://docs.livekit.io/home/self-hosting/deployment">Self-hosting</a> · <a href="https://github.com/livekit/livekit-cli">CLI</a></td></tr>
</tbody>
</table>
<!--END_REPO_NAV-->

# Restaurant Voice Agent with LiveKit and Supabase

A professional voice AI assistant for restaurant reservations using LiveKit Agents, Google Gemini Live API, and Supabase database.

## Features

- **Voice Reservations**: Natural voice interactions for taking restaurant bookings
- **Real-time Database**: Supabase integration for customer data and reservations
- **Availability Checking**: Smart availability checking with alternative suggestions
- **Customer Management**: Automatic customer creation and tracking
- **Call Logging**: Complete call history and transcription
- **Booking Management**: Create, modify, and cancel reservations
- **Menu Integration**: Access to restaurant menu and dietary information
- **Ambience Information**: Restaurant atmosphere and setting details
- **Special Requests**: Seat preferences routed to manager contact
- **FastAPI Backend**: RESTful API for integration with web/mobile apps
- **Manager Routing**: Complex requests automatically routed to management

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Supabase Database

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run the schema from `schema.py` (the `SUPABASE_SCHEMA` constant)
3. Get your project URL and anon key from Project Settings > API

### 3. Configure Environment Variables

Create a `.env` file with the following variables:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# Google/Gemini API Configuration
GOOGLE_API_KEY=your_google_gemini_api_key

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional: Restaurant Information
RESTAURANT_NAME=Your Restaurant Name
RESTAURANT_PHONE=+1234567890
MANAGER_PHONE=+1234567890
```

### 4. Initialize Database with Sample Data

You can manually insert a restaurant record:

```sql
INSERT INTO restaurants (name, address, phone, email, opening_hours, max_capacity) VALUES (
    'Your Restaurant Name',
    '123 Main St, City, State 12345',
    '+1234567890',
    'contact@yourrestaurant.com',
    '{
        "monday": {"open": "17:00", "close": "22:00"},
        "tuesday": {"open": "17:00", "close": "22:00"},
        "wednesday": {"open": "17:00", "close": "22:00"},
        "thursday": {"open": "17:00", "close": "22:00"},
        "friday": {"open": "17:00", "close": "23:00"},
        "saturday": {"open": "17:00", "close": "23:00"},
        "sunday": {"closed": true}
    }',
    50
);
```

### 5. Run the Server

Option A - Use the startup script (recommended):
```bash
python start_server.py
```

Option B - Run FastAPI directly:
```bash
python main.py
```

Option C - Run the agent standalone:
```bash
python agent.py start
```

## How It Works

### Voice Interaction Flow

1. **Customer calls** → Agent greets and asks how to help
2. **Reservation request** → Agent collects date, time, party size, name, phone
3. **Availability check** → System checks database and suggests alternatives if needed
4. **Confirmation** → Booking created with confirmation code
5. **Follow-up** → Customer can modify/cancel using confirmation code

### Database Schema

- **customers**: Customer information and contact details
- **restaurants**: Restaurant information and operating hours
- **bookings**: Reservation details with status tracking
- **call_logs**: Complete call history and transcriptions
- **tables**: Table management (optional for advanced features)
- **menu**: Restaurant menu items with allergen information

### Available Tools

The agent has access to these tools for handling reservations:

- `create_booking_tool()`: Creates new reservations
- `check_availability_tool()`: Checks table availability
- `find_booking_tool()`: Looks up existing bookings
- `cancel_booking_tool()`: Cancels reservations

## API Keys Setup

### Google Gemini API
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GOOGLE_API_KEY`

### LiveKit
1. Sign up at [LiveKit Cloud](https://cloud.livekit.io)
2. Create a new project
3. Get API key and secret from project settings
4. Add to `.env` file

### Supabase
1. Create project at [supabase.com](https://supabase.com)
2. Go to Project Settings > API
3. Copy URL and anon key to `.env` file

## File Structure

```
├── agent.py           # Main agent with voice AI logic
├── main.py            # FastAPI server and API endpoints
├── start_server.py    # Startup script with database initialization
├── database.py        # Supabase database operations
├── schema.py          # Database schema and Pydantic models
├── setup.py           # Package configuration
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## API Endpoints

The FastAPI server provides the following endpoints:

### Core Endpoints
- `GET /health` - Health check and service status
- `GET /restaurant/info` - Restaurant information and hours

### Agent Management
- `POST /agent/start-call` - Start a new agent call session
- `POST /agent/end-call` - End an agent call session
- `POST /agent/deploy` - Deploy the LiveKit agent worker
- `POST /agent/stop` - Stop the agent worker

### Booking Management
- `POST /bookings` - Create a new booking
- `POST /bookings/check-availability` - Check table availability
- `GET /bookings/{confirmation_code}` - Get booking details
- `PUT /bookings/{confirmation_code}/cancel` - Cancel a booking

### Menu & Information
- `POST /menu/search` - Search menu items
- `POST /special-requests` - Handle special requests and route to manager

### Customer Management
- `GET /customers/{phone_number}` - Get customer information and booking history

### Analytics
- `GET /analytics/calls` - Get call analytics and metrics

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8 .
```

### Adding New Features

1. **New database operations**: Add methods to `database.py`
2. **New data models**: Define in `schema.py`
3. **New agent capabilities**: Add tools to `RestaurantAssistant` class
4. **Database schema changes**: Update `SUPABASE_SCHEMA` constant

## Deployment

For production deployment:

1. Use Vertex AI instead of direct Gemini API
2. Set up proper authentication with service accounts
3. Configure Row Level Security (RLS) in Supabase
4. Set up monitoring and logging
5. Use environment-specific configurations

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure all dependencies are installed
2. **Database connection**: Check Supabase URL and API key
3. **Voice not working**: Verify Google API key and model availability
4. **Call tracking**: Ensure phone number is passed in room metadata

### Debug Mode

Set `DEBUG=true` in your `.env` file for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
