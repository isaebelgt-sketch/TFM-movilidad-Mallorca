"""Lectura segura del registro de fuentes autorizado."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "config" / "source_registry.json"


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_source(source_id: str, path: Path = DEFAULT_REGISTRY) -> dict:
    for source in load_registry(path).get("sources", []):
        if source.get("source_id") == source_id:
            return source
    raise KeyError(f"La fuente {source_id!r} no está registrada.")


def require_approved_source(source_id: str, path: Path = DEFAULT_REGISTRY) -> dict:
    source = get_source(source_id, path)
    if source.get("status") != "approved":
        requirement = source.get("activation_requirement", "No existe una autorización de ingesta.")
        raise PermissionError(f"{source_id} no puede ingerirse: {source.get('status')}. {requirement}")
    return source
