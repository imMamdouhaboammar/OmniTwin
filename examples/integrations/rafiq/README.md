# Rafiq Integration Examples

This directory contains design contract examples showing how an application such as
[Rafiq](https://github.com/imMamdouhaboammar/Rafiq-Bot) could call OmniTwin's cognitive
engine to obtain grounded context.

> **Status:** Architectural design using verified OmniTwin APIs.
> A production integration between OmniTwin and Rafiq does not exist today.
> See [docs/integrations/rafiq.md](../../../docs/integrations/rafiq.md) for the full specification.

## Running the Design Contract

```bash
cd /path/to/OmniTwin
PYTHONPATH=src python3 examples/integrations/rafiq/design_contract.py
```

## What This Example Demonstrates

- How Rafiq's application layer would pass session context (tenant, persona, user) to OmniTwin
- How OmniTwin returns a bounded cognitive context pack (< 450 tokens)
- How Rafiq's own LLM generates the final response using that context
- How optional grounding verification would work

## What This Example Does NOT Show

- An actual Rafiq codebase integration (none exists today)
- A production-ready API adapter
- Any real persona data or personal conversations

All personas and conversations are entirely synthetic.
