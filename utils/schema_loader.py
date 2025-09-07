import os
import json
from typing import Optional


def load_schema(name: str) -> Optional[dict]:
    """Load a JSON schema by name.

    Tries several candidate filenames under `utils/schemas/`:
    - name (as-is)
    - name + .json
    - with common DTO prefixes/suffixes (e.g., GetUserDto.json)
    - lowercase variants and _-separated variants
    Returns the parsed JSON object or None if not found.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "schemas"))
    candidates = []
    # direct
    candidates.append(name)
    candidates.append(f"{name}.json")
    # DTO-style: capitalize words, append/strip DTO suffix
    candidates.append(name + ".json")
    # common DTO mapping: user_schema -> GetUserDto.json
    if name.lower().startswith("user"):
        candidates.append("GetUserDto.json")
        candidates.append("UserRoleDto.json")
        candidates.append("UserPermissionDto.json")
    if name.lower().startswith("role"):
        candidates.append("RoleDto.json")
        candidates.append("RolePermissionDto.json")
    # try lowercase and underscored
    name_snake = name.replace('-', '_')
    candidates.append(name_snake.lower())
    candidates.append(name_snake.lower() + ".json")

    tried = set()
    for cand in candidates:
        if not cand:
            continue
        path = os.path.join(base_dir, cand)
        if path in tried:
            continue
        tried.add(path)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                continue
    return None
