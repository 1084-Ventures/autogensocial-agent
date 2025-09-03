#!/usr/bin/env python3
"""
Generate JSON Schemas, YAML variants, and OpenAPI from Pydantic models.

Outputs under src/specs/:
 - schemas/*.json (and *.yaml)
 - openapi.yaml and openapi.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    print("PyYAML is required: pip install pyyaml", file=sys.stderr)
    raise


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SPECS = SRC / "specs"
SCHEMAS_DIR = SPECS / "schemas"

sys.path.insert(0, str(ROOT))

from src.specs.models import (  # noqa: E402
    SCHEMA_MODELS,
    OrchestrateRequest,
    DurableOrchestrationStartResponse,
)
from src.specs.tools_registry import TOOLS, ToolDef  # noqa: E402


def write_json_yaml(obj: dict, json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    yaml_path = json_path.with_suffix(".yaml")
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False)


def write_yaml(obj: dict, yaml_path: Path) -> None:
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False)


def generate_model_schemas() -> None:
    for filename, model in SCHEMA_MODELS.items():
        schema = model.model_json_schema()
        write_json_yaml(schema, SCHEMAS_DIR / filename)


def build_openapi() -> dict:
    # Inline the model schemas as OpenAPI components
    components = {
        "schemas": {
            "OrchestrateRequest": OrchestrateRequest.model_json_schema(),
            "DurableStartResponse": DurableOrchestrationStartResponse.model_json_schema(),
        }
    }

    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "AutogenSocial Functions API",
            "version": "0.1.0",
            "description": "HTTP endpoints exposed by the AutogenSocial Azure Functions app.",
        },
        "servers": [
            {"url": "http://localhost:7071/api", "description": "Local Functions host"}
        ],
        "paths": {
            "/autogensocial/orchestrate": {
                "post": {
                    "summary": "Start the AutogenSocial durable orchestration",
                    "operationId": "startAutogenSocial",
                    "parameters": [
                        {
                            "in": "query",
                            "name": "brandId",
                            "schema": {"type": "string"},
                            "required": False,
                        },
                        {
                            "in": "query",
                            "name": "postPlanId",
                            "schema": {"type": "string"},
                            "required": False,
                        },
                    ],
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/OrchestrateRequest"}
                            }
                        },
                    },
                    "responses": {
                        "202": {
                            "description": "Orchestration accepted; Durable Functions status endpoints returned",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/DurableStartResponse"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Missing brandId or postPlanId",
                            "content": {
                                "text/plain": {"schema": {"type": "string"}}
                            },
                        },
                    },
                }
            }
        },
        "components": components,
    }
    return spec


def generate_openapi() -> None:
    spec = build_openapi()
    write_json_yaml(spec, SPECS / "openapi.json")


def generate_tools_yaml() -> None:
    # Build a reverse map from model -> schema filename
    reverse = {model: filename for filename, model in SCHEMA_MODELS.items()}
    tools: list[dict] = []
    for t in TOOLS:
        assert isinstance(t, ToolDef)
        in_fname = reverse.get(t.input_model)
        out_fname = reverse.get(t.output_model)
        if not in_fname or not out_fname:
            raise KeyError(
                f"Schema filename not found for tool {t.name}: "
                f"input={t.input_model.__name__}, output={t.output_model.__name__}"
            )
        tools.append(
            {
                "name": t.name,
                "description": t.description,
                "input": {"$ref": f"./schemas/{in_fname}"},
                "output": {"$ref": f"./schemas/{out_fname}"},
            }
        )

    doc = {"kind": "function-tools", "version": "0.1.0", "tools": tools}
    write_yaml(doc, SPECS / "tools.yaml")


def main() -> None:
    generate_model_schemas()
    generate_openapi()
    generate_tools_yaml()
    print("Specs generated under src/specs/")


if __name__ == "__main__":
    main()
