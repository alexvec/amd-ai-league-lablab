"""Maps the wire format to the core's names using api_schema.json."""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("api_schema.json")


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text("utf-8"))


def read_request(body: dict, schema: dict) -> dict:
    mapping = schema["request"]
    return {internal: body.get(wire) for internal, wire in mapping.items()}


def write_response(result: dict, schema: dict) -> dict:
    mapping = schema["response"]
    return {mapping.get(key, key): value for key, value in result.items()}
