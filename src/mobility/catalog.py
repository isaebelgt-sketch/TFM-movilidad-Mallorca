"""Acceso de solo lectura al catálogo geográfico curado.

El módulo no geocodifica ni corrige coordenadas: sólo expone registros que ya
han superado el control de calidad spatial del pipeline ``raw -> unified ->
curated``. Así se evita que la API convierta entradas incompletas en datos
aparentemente fiables.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import pandas as pd


@dataclass(frozen=True)
class Place:
    """Punto que puede usarse como origen o destino de una consulta OTP."""

    id: str
    name: str
    latitude: float
    longitude: float
    kind: str
    municipality: str | None = None
    category: str | None = None

    def as_dict(self) -> dict[str, str | float | None]:
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "kind": self.kind,
            "municipality": self.municipality,
            "category": self.category,
        }


class TourismCatalog:
    """Catálogo de alojamientos y destinos cuya geometría ya fue validada."""

    def __init__(self, root: Path):
        self.root = root
        self.curated = root / "data" / "curated"

    @property
    def accommodation_path(self) -> Path:
        official = self.root / "data" / "unified" / "accommodations_official_normalized.geojson"
        return official if official.exists() else self.curated / "accommodations_transport_access_baseline.parquet"

    @property
    def destination_path(self) -> Path:
        latest = self.curated / "latest_tourism_destinations.json"
        if latest.exists():
            import json

            path = self.root / json.loads(latest.read_text(encoding="utf-8"))["parquet_output"].replace("\\", "/")
            if path.exists():
                return path
        return self.curated / "tourism_destinations_transport_access_baseline.parquet"

    @lru_cache(maxsize=1)
    def accommodations(self) -> gpd.GeoDataFrame:
        path = self.accommodation_path
        data = gpd.read_file(path) if path.suffix.lower() in {".geojson", ".json"} else gpd.read_parquet(path)
        data = data.rename(columns={"municipality": "municipality_raw", "group": "group_raw", "subgroup": "subgroup_raw"})
        required = {"accommodation_id", "commercial_name", "municipality_raw", "geometry"}
        missing = required.difference(data.columns)
        if missing:
            raise ValueError(f"La capa de alojamientos no cumple el contrato: {sorted(missing)}")
        return data.loc[data.geometry.notna() & data.geometry.is_valid].copy()

    @lru_cache(maxsize=1)
    def destinations(self) -> gpd.GeoDataFrame:
        data = gpd.read_parquet(self.destination_path)
        required = {"poi_id", "name", "destination_category", "geometry"}
        missing = required.difference(data.columns)
        if missing:
            raise ValueError(f"La capa de destinos no cumple el contrato: {sorted(missing)}")
        return data.loc[data.geometry.notna() & data.geometry.is_valid].copy()

    def accommodation(self, accommodation_id: str) -> Place:
        data = self.accommodations()
        selected = data.loc[data["accommodation_id"].astype(str).eq(str(accommodation_id))]
        if selected.empty:
            raise KeyError(f"Alojamiento no encontrado: {accommodation_id}")
        row = selected.iloc[0]
        return Place(
            id=str(row["accommodation_id"]),
            name=str(row["commercial_name"]),
            latitude=float(row.geometry.y),
            longitude=float(row.geometry.x),
            kind="accommodation",
            municipality=_text_or_none(row.get("municipality_raw")),
            category=_text_or_none(row.get("subgroup_raw")),
        )

    def destination(self, poi_id: str) -> Place:
        data = self.destinations()
        selected = data.loc[data["poi_id"].astype(str).eq(str(poi_id))]
        if selected.empty:
            raise KeyError(f"Destino no encontrado: {poi_id}")
        row = selected.iloc[0]
        return Place(
            id=str(row["poi_id"]),
            name=str(row["name"]),
            latitude=float(row.geometry.y),
            longitude=float(row.geometry.x),
            kind="destination",
            category=_text_or_none(row.get("destination_category")),
        )

    def list_accommodations(
        self, municipality: str | None = None, group: str | None = None, query: str | None = None
    ) -> list[Place]:
        data = self.accommodations()
        if municipality:
            data = data.loc[data["municipality_raw"].astype("string").str.casefold().eq(municipality.casefold())]
        if group and "group_raw" in data:
            data = data.loc[data["group_raw"].astype("string").str.casefold().eq(group.casefold())]
        if query:
            data = data.loc[data["commercial_name"].astype("string").str.contains(query, case=False, na=False, regex=False)]
        return [
            Place(
                id=str(row.accommodation_id),
                name=str(row.commercial_name),
                latitude=float(row.geometry.y),
                longitude=float(row.geometry.x),
                kind="accommodation",
                municipality=_text_or_none(row.municipality_raw),
                category=_text_or_none(getattr(row, "subgroup_raw", None)),
            )
            for row in data.itertuples()
        ]

    def list_destinations(self, category: str | None = None, query: str | None = None) -> list[Place]:
        data = self.destinations()
        if category:
            data = data.loc[data["destination_category"].astype("string").str.casefold().eq(category.casefold())]
        if query:
            data = data.loc[data["name"].astype("string").str.contains(query, case=False, na=False, regex=False)]
        return [
            Place(
                id=str(row.poi_id),
                name=str(row.name),
                latitude=float(row.geometry.y),
                longitude=float(row.geometry.x),
                kind="destination",
                category=_text_or_none(row.destination_category),
            )
            for row in data.itertuples()
        ]


def _text_or_none(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)
