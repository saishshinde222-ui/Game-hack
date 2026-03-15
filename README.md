# Game-hack: AI-Powered Dynamic 2D Entity System

A real-time AI game authoring tool. Type natural language commands into a running Godot game and watch as AI generates sprites, animations, and behaviors on the fly -- no recompile, no reload.

The system connects a **Godot 4.6 2D client** to a **Python MCP server** over WebSocket. The MCP server uses **Seedream 5.0** for sprite generation and **Seedance 1.5 Pro** for animation, then sends structured commands back to Godot to spawn entities, attach behaviors, and update animations at runtime.

## Architecture

```
┌─────────────────────┐   WebSocket (port 9080)   ┌─────────────────────┐
│    Godot Client      │◄─────────────────────────►│    MCP Server       │
│                      │                            │                     │
│  - 2D scene          │   user prompt + context ──►│  - Orchestrator     │
│  - WebSocket server  │                            │  - Seedream client  │
│  - Entity manager    │◄── spawn/behavior cmds ───│  - Seedance client  │
│  - Runtime loader    │                            │  - ffmpeg pipeline  │
│  - Behavior scripts  │                            │                     │
└─────────────────────┘                            └─────────────────────┘
```

**Flow:** User types prompt in Godot UI --> Godot sends prompt + project context over WebSocket --> MCP generates assets (sprites, spritesheets) and plans commands --> MCP sends JSON commands back --> Godot executes them live.

## Prerequisites

- **Godot 4.6** (GL Compatibility renderer)
- **Python 3.11+**
- **ffmpeg** (required for video-to-spritesheet conversion)
- **API Keys:**
  - [fal.ai](https://fal.ai/dashboard) key for Seedance 1.5 Pro (animated sprites)
  - [VolcEngine](https://console.volcengine.com) key for Seedream 5.0 (static sprites)

### Install ffmpeg (if not already installed)

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (scoop)
scoop install ffmpeg
```

## Setup

### 1. Clone and configure the MCP server

```bash
cd mcp-server
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create your `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```
FAL_KEY=your_fal_api_key_here
SEEDREAM_API_KEY=your_seedream_api_key_here
```

### 2. Open the Godot project

Open `godot-client/project.godot` in Godot 4.6. No additional setup needed -- the autoloads (CommandServer, EntityManager) are pre-configured.

## Launching

**Order matters:** Start Godot first (it runs the WebSocket server), then start the MCP server (it connects as a client).

### Step 1: Run the Godot game

Open the project in Godot and press **F5** (or the Play button). You should see:

- A dark background with a small blue placeholder character
- A text input bar at the top left
- Status label reading "Waiting for MCP..."

The Godot console should print:
```
[CmdServer] Listening on ws://localhost:9080
```

### Step 2: Run the MCP server

In a separate terminal:

```bash
cd mcp-server
source .venv/bin/activate
python -m app.main
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once connected, the Godot status label changes to **"MCP connected -- ready"** and the MCP terminal prints:
```
INFO: Connecting to Godot at ws://localhost:9080 ...
INFO: Connected to Godot
```

### Step 3: Health check (optional)

```bash
curl http://localhost:8000/health
# {"status":"ok","godot_connected":true}
```

## How It Works

### Command Protocol

The MCP server sends JSON commands to Godot over WebSocket. Godot executes them immediately:

| Command | What it does |
|---------|-------------|
| `spawn_entity` | Loads a PNG as a `Sprite2D` and places it in the scene |
| `spawn_animated_entity` | Loads a spritesheet as an `AnimatedSprite2D` with frame metadata |
| `update_animation` | Adds or replaces an animation on an existing animated entity |
| `attach_behavior` | Attaches a behavior script (`wander`, `move_to`) to an entity |
| `detach_behavior` | Removes a behavior from an entity |
| `remove_entity` | Removes an entity from the scene |
| `status` | Displays a status message in the UI |

### Entity Types

- **Static entities** (trees, rocks, items): Generated as single PNG sprites via Seedream, spawned as `Sprite2D`
- **Animated entities** (characters, creatures): Generated as a reference sprite via Seedream, animated via Seedance 1.5, converted to spritesheet via ffmpeg, spawned as `AnimatedSprite2D`

### Behaviors

Pre-built behavior scripts that the MCP can attach to any entity:

- **wander** -- Oscillates the entity side-to-side (sine wave motion)
- **move_to** -- Moves the entity toward a target position, emits a signal on arrival

### Fallback Mode

If API keys are not set, the system uses placeholder sprites (small purple squares) so you can still test the full command pipeline without making API calls.

## Demo Script

Below is a step-by-step walkthrough for a polished demo. Each step builds on the last, showing off a different capability.

### Act 1: Static sprite generation

Type into the Godot text box:

> **add a tree**

What happens: The MCP generates a 2D tree sprite via Seedream and sends a `spawn_entity` command. A tree appears in the scene. Wait ~5-10 seconds for generation.

Then try:

> **add a rock**

Another static sprite appears. This shows the system can populate a scene with objects on demand.

### Act 2: Animated character generation

> **create a knight character**

What happens: The MCP generates a reference sprite, then animates it with Seedance 1.5, converts the video to a spritesheet with ffmpeg, and sends `spawn_animated_entity`. A knight with an idle breathing animation appears. This takes ~30-60 seconds (video generation is the bottleneck).

### Act 3: Behaviors

> **make the knight wander**

What happens: The MCP sends an `attach_behavior` command. The knight starts oscillating side to side immediately. No new assets generated -- this is instant.

### Act 4: More entities

> **add a sword**

A sword sprite is generated and placed in the scene. Items are detected automatically and rendered as icon-style sprites.

> **add a castle**

A castle sprite appears. The scene is now populated with multiple AI-generated entities.

### Act 5: Animation updates

> **make the knight walk**

What happens: Seedance generates a walk animation, converts to spritesheet, and sends `update_animation`. The knight switches from idle to a walk cycle.

### Act 6: Cleanup

> **remove the tree**

The tree is removed from the scene. Show that entities can be managed dynamically.

### Tips for a Great Demo

1. **Start Godot first, then MCP.** The connection handshake is visible in the status bar -- it looks intentional and professional.
2. **Talk while assets generate.** Generation takes 5-60 seconds. Explain what's happening: "Right now Seedream is generating a sprite... and now Seedance is animating it..."
3. **Start with static objects** (trees, rocks) because they generate in ~5 seconds. Save animated characters for the big reveal.
4. **Show the fallback.** If you want to demo without API keys, the pipeline still works end-to-end with purple placeholder squares -- useful for showing the architecture.
5. **Keep the Godot console visible** (or a second monitor). The `[EntityMgr]` and `[CmdServer]` logs show exactly what's happening in real time.
6. **Show the spritesheet.** After an animated entity is generated, open the `mcp-server/assets/` folder and show the spritesheet PNG -- people love seeing the frame grid.

## Project Structure

```
Game-hack/
├── godot-client/                 # Godot 4.6 project
│   ├── project.godot             # Project config (GL Compatibility, autoloads)
│   ├── scenes/
│   │   └── main.tscn             # 2D scene: background, camera, character, UI
│   ├── scripts/
│   │   ├── main.gd               # Command routing, context gathering, UI
│   │   ├── runtime_loader.gd     # PNG texture + spritesheet loader
│   │   ├── autoloads/
│   │   │   ├── command_server.gd  # WebSocket server (port 9080)
│   │   │   └── entity_manager.gd  # Entity registry + lifecycle
│   │   └── behaviors/
│   │       ├── wander.gd          # Side-to-side oscillation
│   │       └── move_to.gd         # Move toward target position
│   └── assets/
│       └── sprites/               # MCP-generated sprites land here
│
├── mcp-server/                    # Python FastAPI server
│   ├── app/
│   │   ├── main.py                # FastAPI app, WebSocket client to Godot
│   │   ├── orchestrator.py        # NLP command parsing, asset generation pipeline
│   │   ├── clients/
│   │   │   ├── seedream.py        # Seedream 5.0 image generation
│   │   │   └── seedance.py        # Seedance 1.5 Pro video generation (fal.ai)
│   │   └── utils/
│   │       └── sprites.py         # ffmpeg video-to-spritesheet conversion
│   ├── requirements.txt
│   └── .env.example
│
└── README.md
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Godot says "Waiting for MCP..." forever | Make sure the MCP server is running and can reach `ws://localhost:9080` |
| MCP says "Godot not available, retrying..." | Start the Godot game first (it hosts the WebSocket server) |
| Sprites don't appear | Check that the texture path in the command is an absolute path that exists on disk |
| Animated entity shows as static | Check MCP logs for Seedance/ffmpeg errors. Is `ffmpeg` installed? Is `FAL_KEY` set? |
| Purple placeholder instead of real sprite | `SEEDREAM_API_KEY` is not set in `.env`. This is intentional fallback behavior |
| "Command not recognized" status | The orchestrator uses keyword matching. Rephrase using words like "add", "create", "spawn" for entities |

## Without API Keys

The entire pipeline works without API keys -- you just get placeholder sprites instead of AI-generated ones. This is useful for:

- Testing the WebSocket communication
- Verifying entity spawning and behavior attachment
- Developing new features without burning API credits
- Demoing the architecture without network dependencies
