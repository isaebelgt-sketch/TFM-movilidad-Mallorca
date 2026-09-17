from pathlib import Path

from src.mobility.catalog import TourismCatalog


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_prefers_current_validated_sources_when_available():
    catalog = TourismCatalog(ROOT)
    assert catalog.accommodation_path.name == "accommodations_official_normalized.geojson"
    assert catalog.destination_path.name.startswith("tourism_destinations_osm_")
    assert len(catalog.accommodations()) == 1461
    assert len(catalog.destinations()) > 0
