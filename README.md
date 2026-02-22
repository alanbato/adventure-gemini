# Colossal Cave Adventure over Gemini

A faithful port of the classic 350-point [Colossal Cave Adventure](https://en.wikipedia.org/wiki/Colossal_Cave_Adventure) (Crowther & Woods, 1977) served over the [Gemini protocol](https://geminiprotocol.net/). Players explore the cave, solve puzzles, and collect treasure — all through a Gemini client.

Built with [xitzin](https://github.com/alanbato/xitzin) (a Gemini web framework) and [nauyaca](https://github.com/alanbato/nauyaca) (a Gemini server).

## Features

- Full 350-point game with all rooms, items, puzzles, and encounters from the original
- Player authentication via Gemini client certificates
- Per-player game state persisted in SQLite
- Dwarf and pirate encounters with faithful AI behavior
- Structured logging with optional fingerprint hashing for privacy

## Quickstart

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync

# Generate TLS certificates (required for Gemini)
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
  -days 365 -nodes -keyout key.pem -out cert.pem \
  -subj "/CN=localhost"

# Start the server
ADVENTURE_CERTFILE=cert.pem ADVENTURE_KEYFILE=key.pem uv run adventure
```

Then connect with any Gemini client to `gemini://localhost:1965/`.

## Configuration

All settings are read from environment variables prefixed with `ADVENTURE_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./adventure.db` | SQLite database path |
| `HOST` | `localhost` | Bind address |
| `PORT` | `1965` | Bind port |
| `CERTFILE` | — | Path to TLS certificate (required) |
| `KEYFILE` | — | Path to TLS private key (required) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FILE` | — | Log to file instead of stdout |
| `JSON_LOGS` | `false` | Output logs as JSON |
| `HASH_FINGERPRINTS` | `true` | Hash client fingerprints in logs for privacy |

## Project Structure

```
src/adventure/
├── engine/          # Synchronous, pure-Python game logic
│   ├── world.py     # Immutable data structures (Room, Obj, Word, Hint, World)
│   ├── state.py     # Mutable GameState (position, inventory, lamp, dwarves, score)
│   ├── loader.py    # Parses the 12-section advent.dat into a World
│   └── commands.py  # Command dispatch: movement, items, puzzles, combat, scoring
├── routes/          # Xitzin route handlers
│   ├── play.py      # Game routes (require client certificate)
│   └── home.py      # Public pages: /, /help, /about
├── templates/       # Jinja2 .gmi templates for Gemtext responses
├── app.py           # App factory
├── config.py        # Configuration from environment variables
├── logging.py       # structlog setup
├── models.py        # SQLModel entities (Player, SavedGame)
├── session.py       # Load/save/reset game state from DB
└── users.py         # Player upsert by fingerprint
data/
└── advent.dat       # Original game data file
```

## Development

```bash
# Run tests
uv run pytest

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run ty check src/
```

## Credits

- **Original game**: Will Crowther (1976) and Don Woods (1977)
- **Data file format**: Public domain
- **Parsing reference**: Brandon Rhodes' [python-adventure](https://github.com/brandon-rhodes/python-adventure) (Apache 2.0)

## License

MIT
