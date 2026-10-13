# Integrating Custom LLMs with OmniTwin

OmniTwin is provider-agnostic. While it includes an offline deterministic simulator for zero-credential testing, you can easily plug in any commercial or open-weight language model.

---

## 1. Using Supported Cloud Providers

OmniTwin includes built-in adapters for OpenRouter, Google Vertex AI / Gemini, and PI Gateway:

### A. OpenRouter (Access to Claude, GPT-4o, Llama 3, DeepSeek)
Set your API key:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
export OPENROUTER_MODEL="anthropic/claude-3.5-sonnet"
```

### B. Google Vertex AI / Gemini
Set your credentials:
```bash
export GEMINI_API_KEY="AIzaSy..."
# Or use Vertex AI Application Default Credentials:
export GCP_PROJECT_ID="your-project-id"
export GCP_LOCATION="us-central1"
```

---

## 2. Implementing a Custom LLM Provider

To integrate a custom model (e.g. local Ollama, vLLM, or proprietary enterprise endpoint), subclass `BaseLLMProvider`:

```python
from omnitwin.adapters.llm_provider import BaseLLMProvider
import requests

class OllamaProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "llama3:latest", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    @property
    def name(self) -> str:
        return f"ollama-{self.model_name}"

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_message,
            "stream": False,
        }
        res = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60.0)
        res.raise_for_status()
        return res.json()["response"].strip()
```

### Passing to CognitiveGenerator:

```python
from omnitwin import ContourEngine, StateReducer, TurnPlanner, CognitiveGenerator

contour = ContourEngine("twin.db")
reducer = StateReducer("twin.db")
planner = TurnPlanner(contour, reducer)

ollama_provider = OllamaProvider("llama3:latest")
generator = CognitiveGenerator(
    contour=contour,
    reducer=reducer,
    planner=planner,
    provider=ollama_provider,
)

result = generator.execute_turn(
    persona_id="alex",
    user_id="user_01",
    user_message="What are your thoughts on consensus protocols?",
)
print(result["answer"])
```

The `CognitiveGenerator` will compile the bounded context, invoke your custom provider, extract citations, enforce "No ID, No Claim", and verify semantic entailment automatically.
