# Getting Started with OmniTwin

OmniTwin is an open-source cognitive and behavioral continuity engine designed to give AI agents persistent identity, grounded memory, and relational awareness.

---

## 1. System Requirements

- **Python**: 3.9, 3.10, 3.11, or 3.12
- **Node/Bun**: [Bun](https://bun.sh) v1.0+ (required for `@omnitwin/gateway`)
- **OS**: macOS, Linux, or Windows (WSL2 recommended)
- **SQLite**: 3.35+ (with FTS5 enabled; standard in Python 3.9+)

---

## 2. Quick Installation

```bash
# Clone the repository
git clone https://github.com/imMamdouhaboammar/OmniTwin.git
cd OmniTwin

# Install the Python package in editable development mode
pip install -e .

# Or using uv:
uv pip install -e .
```

Verify your installation:

```bash
omnitwin --version
# Output: OmniTwin v0.1.0 - Cognitive Continuity for AI Agents
```

---

## 3. Creating Your First Persona Pack

An OmniTwin persona is defined as a clean JSON document. Here is an example `companion.json`:

```json
{
  "persona_id": "companion",
  "name": "Companion",
  "tenant_id": "default",
  "title": "Autonomous Research Assistant",
  "traits": ["analytical", "concise", "epistemically humble"],
  "core_identity": [
    "Graduated in Computer Science with a specialization in distributed systems.",
    "Works on fault-tolerant storage architectures and local-first software.",
    "Values clarity, reproducible benchmarks, and failing closed."
  ],
  "preferences": {
    "editor": "Neovim",
    "coffee": "Light roast pour-over",
    "os": "Linux"
  },
  "negative_constraints": [
    "Never provides medical diagnoses or clinical advice.",
    "Never fabricates personal memories without an authorized citation."
  ],
  "relationships": [
    {
      "user_id": "lead_developer",
      "role": "collaborator",
      "closeness": 0.70,
      "trust": 0.85,
      "teasing_permission": 0.50,
      "romantic_assumption_allowed": false,
      "initial_mood": "focused",
      "initial_energy": 0.85
    }
  ]
}
```

Import your persona into a local database:

```bash
omnitwin init --persona companion.json --persona-id companion
```

---

## 4. Querying from Python

```python
from omnitwin import ContourEngine, StateReducer, TurnPlanner, CognitiveGenerator

db_path = "omnitwin.db"

contour = ContourEngine(db_path)
reducer = StateReducer(db_path)
planner = TurnPlanner(contour, reducer)
generator = CognitiveGenerator(contour=contour, reducer=reducer, planner=planner)

# Execute grounded turn
result = generator.execute_turn(
    persona_id="companion",
    user_id="lead_developer",
    user_message="What editor do you prefer for writing code?",
)

print("Agent Response:", result["answer"])
print("Grounding Verified:", result["verified"])
print("Cited Evidence Nodes:", result["cited_ids"])
print("Remaining Energy:", result["state"]["energy"])
```

---

## 5. Starting the gRPC Core & Web Console

To run OmniTwin as a persistent service:

```bash
# Start gRPC Core
omnitwin serve --host 127.0.0.1 --port 50051 --db omnitwin.db
```

In a separate terminal, launch the Twin Gateway:

```bash
cd services/twin-gateway
bun install
bun run start
```

Open your browser to `http://localhost:3030` to test grounded conversations and wearable telemetry ingestion in real time.
