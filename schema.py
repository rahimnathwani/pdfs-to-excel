"""Schema builder: reads a YAML config and builds a dynamic Pydantic model."""

from typing import Literal, NamedTuple, get_args
from pathlib import Path

import yaml
from pydantic import Field, create_model


VALID_TYPES = {"string", "integer", "float", "boolean"}

TYPE_MAP = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
}


class SchemaConfig(NamedTuple):
    model_class: type
    openai_model: str
    system_prompt: str


def _validate_yaml(data: dict) -> None:
    """Validate that the YAML data has the required structure."""
    for key in ("model", "system_prompt", "fields"):
        if key not in data:
            raise ValueError(f"Missing required key: {key!r}")

    if not isinstance(data["fields"], list) or len(data["fields"]) == 0:
        raise ValueError("'fields' must be a non-empty list")

    for i, field in enumerate(data["fields"]):
        for req in ("name", "type", "description"):
            if req not in field:
                raise ValueError(f"Field at index {i} is missing required key: {req!r}")

        ftype = field["type"]
        if ftype not in VALID_TYPES:
            raise ValueError(
                f"Field {field['name']!r} has invalid type {ftype!r}. "
                f"Valid types: {', '.join(sorted(VALID_TYPES))}"
            )


def _build_field_type(field: dict):
    """Return the Python type for a YAML field definition."""
    if "choices" in field:
        choices = tuple(field["choices"])
        return Literal[choices]
    return TYPE_MAP[field["type"]]


def load_schema(yaml_path: str, include_citations: bool = True) -> SchemaConfig:
    """Load a YAML schema file and return a SchemaConfig with a dynamic Pydantic model.

    Args:
        yaml_path: Path to the YAML configuration file.
        include_citations: If True, add a ``{name}_citation: str | None`` field
            for each defined field.

    Returns:
        A SchemaConfig named tuple containing the Pydantic model class,
        the OpenAI model name, and the system prompt.
    """
    raw = Path(yaml_path).read_text()
    data = yaml.safe_load(raw)

    _validate_yaml(data)

    field_definitions: dict = {}

    for field in data["fields"]:
        name = field["name"]
        py_type = _build_field_type(field)
        description = field["description"]

        field_definitions[name] = (py_type, Field(description=description))

        if include_citations:
            field_definitions[f"{name}_citation"] = (
                str | None,
                Field(default=None, description=f"Citation for {name}"),
            )

    model_class = create_model("ExtractedData", **field_definitions)

    return SchemaConfig(
        model_class=model_class,
        openai_model=data["model"],
        system_prompt=data["system_prompt"],
    )
