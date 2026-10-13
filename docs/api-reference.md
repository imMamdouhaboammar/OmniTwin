# OmniTwin API & Protocol Reference

OmniTwin exposes two primary interfaces:
1. **Native East-West gRPC Service**: High-performance internal interface for agent orchestration (Port `50051`).
2. **Twin Gateway REST & WebSocket Service**: Public streaming and client interface (Port `3030`).

---

## 1. East-West gRPC Service (`CognitiveEngineService`)

Defined in `proto/twin_engine.proto`:

### RPC Methods

#### `OpenIntent(IntentRequest) -> IntentResponse`
Opens a new auditable run ticket for an interaction turn.
- **Request**:
  - `character_slug`: Persona identifier (e.g. `"alex"`).
  - `user_id`: Identifier of the interlocutor.
  - `user_message`: Incoming message text.
- **Response**:
  - `run_id`: Unique run ticket string.
  - `character_slug`: Persona identifier.
  - `created_at_unix`: Timestamp in seconds.

#### `PlanTurn(PlanTurnRequest) -> PlanTurnResponse`
Executes intent evaluation, retrieves candidate EPs, and locks the delivery slice into the database.

#### `VerifyTurn(VerifyTurnRequest) -> VerifyTurnResponse`
Validates model output against "No ID, No Claim" and semantic entailment invariants.
- **Request**:
  - `run_id`: The active run ticket.
  - `cited_ep_ids`: List of cited EP IDs found in model response.
- **Response**:
  - `is_accepted`: Boolean flag indicating whether the turn passed verification.
  - `missing_ep_ids`: List of cited IDs that were unauthorized or absent.
  - `rejection_reason`: Explanation if rejected.

#### `IngestBiometrics(BiometricTelemetryRequest) -> BiometricTelemetryResponse`
Ingests R-R interval telemetry to update allostatic load and conversational appetite.
- **Request**:
  - `character_slug`: Persona identifier.
  - `user_id`: Interlocutor identifier.
  - `rr_intervals_ms`: Array of R-R intervals in milliseconds.
  - `heart_rate`: Mean heart rate in BPM.
- **Response**:
  - `rmssd`: Root mean square of successive differences.
  - `stress_index`: Baevsky Stress Index.
  - `energy`: Computed physical energy score [0.0, 1.0].

#### `ExecuteTurn(ExecuteTurnRequest) -> ExecuteTurnResponse`
Executes an end-to-end cognitive turn (plan, generate, verify, and state reduction).

---

## 2. Twin Gateway REST Endpoints

### `POST /api/v1/twin/turn`
Executes a grounded conversational turn.

**Request Body (JSON):**
```json
{
  "personaId": "alex",
  "userId": "collaborator",
  "message": "What database do you recommend for local agents?"
}
```

**Response (JSON):**
```json
{
  "runId": "run_9a8b7c6d5e4f",
  "verified": true,
  "socialMove": "give_opinion",
  "bubbles": [
    "From my perspective: Prefers local-first SQLite architectures with deterministic state machines.."
  ],
  "answer": "From my perspective: Prefers local-first SQLite architectures with deterministic state machines..",
  "energy": 0.78,
  "mood": "focused",
  "appetite": "chatty",
  "deliveredCount": 1,
  "transport": "grpc"
}
```

---

### `POST /api/v1/twin/telemetry`
Ingests wearable sensor streams (e.g. Apple Watch HealthKit or Polar R-R streams).

**Request Body (JSON):**
```json
{
  "personaId": "alex",
  "rrIntervalsMs": [800, 815, 790, 810, 805, 820, 795, 800],
  "sleepHours": 7.5
}
```

**Response (JSON):**
```json
{
  "rmssd": 52.4,
  "stress_index": 42.1,
  "energy": 0.82,
  "conversation_appetite": "chatty",
  "mood": "calm",
  "transport": "grpc"
}
```

---

### `GET /api/v1/twin/autonomic`
Retrieves current autonomic state and allostatic load for a persona.

**Query Parameters:**
- `personaId`: Persona identifier (e.g., `?personaId=alex`).

---

### `GET /health`
Service health check endpoint.

```json
{
  "status": "healthy",
  "service": "omnitwin-gateway",
  "runtime": "bun",
  "timestamp": "2026-10-13T07:00:00.000Z"
}
```

---

## 3. WebSocket Streaming Interface

### Endpoint: `/ws/chat`
Provides real-time typing indicators and cadenced chat bubbles.

**Client Message (JSON):**
```json
{
  "personaId": "alex",
  "userId": "collaborator",
  "message": "Hello Alex!"
}
```

**Server Stream Messages:**
1. `{"type": "status", "status": "typing"}`
2. `{"type": "bubble", "index": 0, "total": 2, "text": "Hey there!", "verified": true, "socialMove": "check_in"}`
3. `{"type": "bubble", "index": 1, "total": 2, "text": "Good to hear from you.", "verified": true, "socialMove": "check_in"}`
4. `{"type": "done"}`
