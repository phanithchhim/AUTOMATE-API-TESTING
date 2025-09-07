#!/usr/bin/env python3
"""Generate JSON Schema files from Java DTO classes.

This is a lightweight parser that looks for `private <Type> <name>;` fields in Java files
under the `src/main/java/com/cmsportal/model/dto` directory and emits a JSON Schema for
each class under `AUTOMATE-API-TESTING/utils/schemas/`.

It handles common types: String, Integer, Long, int, long, boolean, Boolean, Double, Float
and will map unknown types to string by default. Collections like List<...> are treated as arrays.

Run from project root (PowerShell):

    python tools\generate_schemas_from_dto.py

The script does not depend on the testing venv; it uses only the Python stdlib.
"""
import re
import os
import json
from pathlib import Path


JAVA_SRC = Path("src/main/java/com/cmsportal/model/dto")
OUT_DIR = Path(__file__).resolve().parents[1] / "utils" / "schemas"

TYPE_MAP = {
    "String": "string",
    "Integer": "integer",
    "int": "integer",
    "Long": "integer",
    "long": "integer",
    "Boolean": "boolean",
    "boolean": "boolean",
    "Double": "number",
    "double": "number",
    "Float": "number",
    "float": "number",
}


def java_type_to_schema(typ: str):
    # remove generics
    typ = typ.strip()
    if typ.endswith("[]"):
        # array of primitive
        inner = typ[:-2]
        return {"type": "array", "items": {"type": TYPE_MAP.get(inner, "string")}}
    if "<" in typ and ">" in typ:
        base, inner = typ.split("<", 1)
        inner = inner.rsplit(">", 1)[0]
        if base.strip().endswith("List") or base.strip().endswith("ArrayList"):
            item_type = TYPE_MAP.get(inner.strip(), "string")
            return {"type": "array", "items": {"type": item_type}}
        # fallback treat as object/string
        return {"type": "string"}
    return {"type": TYPE_MAP.get(typ, "string")}


def parse_java_fields(java_text: str):
    # very simple: find lines like 'private Type name;' or 'private Type name = ...;'
    pattern = re.compile(r"private\s+([\w<>\[\]]+)\s+(\w+)\s*(?:=\s*[^;]+)?;")
    fields = []
    for m in pattern.finditer(java_text):
        typ, name = m.group(1), m.group(2)
        fields.append((name, typ))
    return fields


def generate_schema_for_file(java_path: Path):
    text = java_path.read_text(encoding="utf-8")
    # try to find class name
    m = re.search(r"public\s+class\s+(\w+)", text)
    class_name = m.group(1) if m else java_path.stem
    fields = parse_java_fields(text)
    schema = {"$schema": "http://json-schema.org/draft-07/schema#", "title": class_name, "type": "object", "properties": {}, "required": []}
    for name, typ in fields:
        schema_prop = java_type_to_schema(typ)
        schema["properties"][name] = schema_prop
        # assume fields are optional; only add to required if primitive non-nullable
    # write file
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / f"{class_name}.json"
    out_file.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {out_file}")


def main():
    if not JAVA_SRC.exists():
        print(f"Java DTO source directory not found: {JAVA_SRC}")
        return
    java_files = list(JAVA_SRC.rglob("*.java"))
    if not java_files:
        print("No Java DTO files found")
        return
    for f in java_files:
        generate_schema_for_file(f)


if __name__ == "__main__":
    main()
