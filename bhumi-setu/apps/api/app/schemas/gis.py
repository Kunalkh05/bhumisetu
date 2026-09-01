"""Gated GIS response models."""

from __future__ import annotations

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = [
    "BboxOut",
    "ClusterFeatureOut",
    "ParcelBboxOut",
    "ParcelGeometryFeatureOut",
    "ParcelMapOut",
]


class BboxOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    min_lon: float = Sensitive(Visibility.PUBLIC)
    min_lat: float = Sensitive(Visibility.PUBLIC)
    max_lon: float = Sensitive(Visibility.PUBLIC)
    max_lat: float = Sensitive(Visibility.PUBLIC)


class ParcelGeometryFeatureOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    parcel_id: int = Sensitive(Visibility.PUBLIC)
    survey_number: str = Sensitive(Visibility.PUBLIC)
    sub_division: str | None = Sensitive(Visibility.PUBLIC)
    area_code: str = Sensitive(Visibility.PUBLIC)
    geojson: dict = Sensitive(Visibility.PUBLIC)


class ParcelBboxOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    bbox: BboxOut = Sensitive(Visibility.PUBLIC)
    simplification_tolerance: float = Sensitive(Visibility.PUBLIC)
    limit: int = Sensitive(Visibility.PUBLIC)
    geometry_simplified: bool = Sensitive(Visibility.PUBLIC)
    coordinate_decimals: int = Sensitive(Visibility.PUBLIC)
    features: list[ParcelGeometryFeatureOut] = Sensitive(Visibility.PUBLIC)


class ClusterFeatureOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    lon: float = Sensitive(Visibility.PUBLIC)
    lat: float = Sensitive(Visibility.PUBLIC)
    count: int = Sensitive(Visibility.PUBLIC)


class ParcelMapOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    mode: str = Sensitive(Visibility.PUBLIC)
    bbox: BboxOut = Sensitive(Visibility.PUBLIC)
    count: int = Sensitive(Visibility.PUBLIC)
    cluster_cell_size_deg: float | None = Sensitive(Visibility.PUBLIC)
    clusters: list[ClusterFeatureOut] = Sensitive(Visibility.PUBLIC)
    parcels: list[ParcelGeometryFeatureOut] = Sensitive(Visibility.PUBLIC)
