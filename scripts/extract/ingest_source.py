"""Ingiere una fuente aprobada en un snapshot raw inmutable.

La descarga remota exige ``--execute``. Sin ese argumento el script sólo
informa de la operación prevista, evitando que una ejecución accidental cambie
los datos de trabajo. Para fuentes autenticadas se usa ``--input`` con el
fichero descargado manualmente desde el proveedor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_pipeline.source_registry import DEFAULT_REGISTRY, require_approved_source


RAW = ROOT / "data" / "raw"
SNAPSHOT_DOCS = ROOT / "docs" / "source_snapshots"
CHUNK_SIZE = 1024 * 1024


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def suffix_for(source: dict, input_path: Path | None = None) -> str:
    if input_path:
        return input_path.suffix or ".bin"
    suffix = Path(urlparse(str(source["download_url"])).path).suffix
    return suffix or ".bin"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, timeout: int = 90) -> tuple[int, dict[str, str], int, str]:
    """Descarga en streaming y sólo publica el fichero tras completarlo."""
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    try:
        request = Request(url, headers={"User-Agent": "TFM-Mallorca-Data-Pipeline/1.0"})
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            with temporary.open("wb") as stream:
                while chunk := response.read(CHUNK_SIZE):
                    stream.write(chunk)
                    digest.update(chunk)
                    total += len(chunk)
            if total == 0:
                raise ValueError("La respuesta remota no contenía datos.")
            temporary.replace(destination)
            headers = {key.lower(): value for key, value in response.headers.items()}
            return status, headers, total, digest.hexdigest()
    except (HTTPError, URLError) as error:
        temporary.unlink(missing_ok=True)
        raise ConnectionError(f"No se pudo descargar {url}: {error}") from error
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def write_manifest(source: dict, run_id: str, payload: Path, acquisition: dict) -> Path:
    manifest = {
        "source_id": source["source_id"],
        "provider": source["provider"],
        "source_url": source["source_url"],
        "download_url": source["download_url"],
        "license": source["license"],
        "attribution": source["attribution"],
        "coverage": source["coverage"],
        "data_kind": source["data_kind"],
        "status_at_ingestion": source["status"],
        "run_id": run_id,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        "payload_file": payload.name,
        "payload_bytes": payload.stat().st_size,
        "payload_sha256": sha256_file(payload),
        **acquisition,
    }
    snapshot_dir = payload.parent
    snapshot_manifest = snapshot_dir / "manifest.json"
    snapshot_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    SNAPSHOT_DOCS.mkdir(parents=True, exist_ok=True)
    documentation_manifest = SNAPSHOT_DOCS / f"{source['source_id']}_{run_id}.json"
    documentation_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = snapshot_dir.parent / "latest.json"
    latest.write_text(json.dumps({"run_id": run_id, "manifest": str(snapshot_manifest.relative_to(ROOT))}, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot_manifest


def ingest(source_id: str, execute: bool, input_path: Path | None, registry_path: Path) -> dict:
    source = require_approved_source(source_id, registry_path)
    if input_path is not None and not input_path.is_file():
        raise FileNotFoundError(f"No existe el fichero de entrada: {input_path}")
    mode = "manual_file" if input_path else "remote_download"
    if input_path is None and not source.get("automated_download"):
        raise PermissionError(
            f"{source_id} no permite descarga automatizada. Descarga el fichero desde el proveedor y usa --input RUTA."
        )
    if not execute:
        return {
            "status": "dry_run",
            "source_id": source_id,
            "mode": mode,
            "download_url": source["download_url"],
            "message": "No se ha descargado ni escrito ningún dato. Añade --execute para crear un snapshot raw.",
        }
    run_id = utc_run_id()
    snapshot_dir = RAW / source_id / run_id
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    payload = snapshot_dir / f"payload{suffix_for(source, input_path)}"
    if input_path:
        shutil.copy2(input_path, payload)
        acquisition = {"acquisition_mode": "manual_file", "http_status": None, "response_headers": {}}
    else:
        status, headers, downloaded_bytes, streamed_sha256 = download(source["download_url"], payload)
        acquisition = {
            "acquisition_mode": "remote_download",
            "http_status": status,
            "response_headers": {key: headers[key] for key in ("content-type", "content-length", "etag", "last-modified") if key in headers},
            "downloaded_bytes": downloaded_bytes,
            "streamed_sha256": streamed_sha256,
        }
    manifest = write_manifest(source, run_id, payload, acquisition)
    return {"status": "ingested", "source_id": source_id, "payload": str(payload.relative_to(ROOT)), "manifest": str(manifest.relative_to(ROOT))}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingiere una fuente approved como snapshot raw trazable.")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--execute", action="store_true", help="Autoriza la descarga/copia. Sin este flag se ejecuta dry-run.")
    parser.add_argument("--input", type=Path, help="Fichero descargado manualmente para fuentes autenticadas.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    result = ingest(args.source_id, args.execute, args.input, args.registry)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
