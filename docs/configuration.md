# OmniTwin Configuration & Environment Reference

OmniTwin can be configured via environment variables, configuration files (`config/*.yaml`), and command-line arguments.

---

## 1. Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `OMNITWIN_DB_PATH` | `omnitwin.db` | Path to the local SQLite database file. |
| `OMNITWIN_AUTH_TOKEN` | *None* | Optional bearer token required for gRPC and API access. |
| `PORT` | `3030` | HTTP port for the Twin Gateway service. |
| `GRPC_ADDR` | `localhost:50051` | Host and port of the upstream Cognitive Core gRPC service. |
| `OMNITWIN_PROTO_PATH` | *Auto-detected* | Explicit filesystem path to `twin_engine.proto`. |
| `PI_GATEWAY_URL` | *None* | Base URL for private PI Gateway LLM proxy. |
| `PI_GATEWAY_KEY` | *None* | API key for private PI Gateway LLM proxy. |
| `OPENROUTER_API_KEY` | *None* | API key for OpenRouter multi-model LLM access. |
| `GEMINI_API_KEY` | *None* | API key for direct Google Vertex / Gemini API calls. |
| `GCP_PROJECT_ID` | *None* | Google Cloud Project ID for Vertex AI. |
| `GCP_LOCATION` | `us-central1` | Google Cloud Region for Vertex AI. |

---

## 2. Configuration Profiles (`config/`)

OmniTwin includes structured configuration templates in the `config/` directory:

- `config/default_profile.yaml`: Default pacing thresholds, energy decay rates, and conversation appetite boundaries.
- `config/verification_depth.yaml`: Contour verification strictness (enabling/disabling semantic entailment checks and threshold tolerances).
- `config/barrier_schema.json`: JSON schema for validating incoming wearable telemetry packets.
- `config/intake_form_schema.json`: JSON schema for validating persona pack imports.

---

## 3. Production Security Checklist

When deploying OmniTwin in multi-user or production environments:
1. **Never bind to 0.0.0.0 without TLS**: Ensure the gRPC server binds to `127.0.0.1` unless running behind a reverse proxy (e.g. Envoy, NGINX) with mutual TLS.
2. **Set `OMNITWIN_AUTH_TOKEN`**: Prevent unauthorized RPC invocations by enabling the bearer authentication interceptor.
3. **Protect Database Permissions**: Ensure SQLite database files have file permissions `600` (`chmod 600 omnitwin.db`) so only the service user can read persona data.
4. **Regular Backup of SQLite Store**: Use SQLite's online backup API or `sqlite3 .backup` to snapshot state without service downtime.
