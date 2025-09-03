AutogenSocial Specs

This folder documents core contracts and interfaces for the AutogenSocial Functions app.

Contents

- models/: Pydantic models used to describe request/response shapes
- schemas/: JSON Schemas for key payloads and documents
- openapi.yaml: Public HTTP endpoints (generated)
- workflow.yaml: Durable workflow outline and steps (hand-authored for now)
- tools.yaml: Function-tool contracts for agent integrations (generated)
- config.schema.json: Environment configuration schema

Usage

- Reference these when adding new endpoints, activities, or tools to keep interfaces consistent.
- Schemas are minimal and evolve with the implementation; prefer additive changes.

Generation

- Run `python scripts/generate_specs.py` to regenerate JSON Schemas and OpenAPI
  from the Pydantic models in `src/specs/models/`.
- The same command also generates `tools.yaml` from `src/specs/tools_registry.py`,
  which references the schemas produced from the Pydantic models.
