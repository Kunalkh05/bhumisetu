/**
 * GIS and geospatial type definitions for the BHUMISETU platform.
 * Used in map visualizations and parcel boundary management.
 */

/** Geographic coordinate pair (WGS84) */
export interface Coordinate {
  latitude: number;
  longitude: number;
}

/** Bounding box for map viewport */
export interface BoundingBox {
  northEast: Coordinate;
  southWest: Coordinate;
}

/** GeoJSON geometry types supported */
export type GeometryType = 'Point' | 'LineString' | 'Polygon' | 'MultiPolygon';

/** GeoJSON Feature for parcel boundaries */
export interface ParcelFeature {
  type: 'Feature';
  geometry: {
    type: GeometryType;
    coordinates: number[] | number[][] | number[][][] | number[][][][];
  };
  properties: ParcelProperties;
}

/** Properties attached to each parcel GeoJSON feature */
export interface ParcelProperties {
  parcelId: string;
  surveyNumber: string;
  subDivision?: string;
  village: string;
  taluka: string;
  district: string;
  areaSqm: number;
  landUse: string;
  ownerName?: string;
  caseId?: string;
  acquisitionStatus?: 'not_acquired' | 'in_progress' | 'acquired';
  fillColor?: string;
  strokeColor?: string;
  opacity?: number;
}

/** GeoJSON FeatureCollection for batch parcel rendering */
export interface ParcelFeatureCollection {
  type: 'FeatureCollection';
  features: ParcelFeature[];
}

/** Map layer configuration */
export interface MapLayer {
  id: string;
  name: string;
  type: 'parcels' | 'boundaries' | 'roads' | 'satellite' | 'revenue';
  visible: boolean;
  opacity: number;
  source: string;
  minZoom?: number;
  maxZoom?: number;
}

/** Map marker for point-of-interest display */
export interface MapMarker {
  id: string;
  position: Coordinate;
  label: string;
  type: 'case_location' | 'office' | 'survey_point' | 'infrastructure';
  icon?: string;
  popupContent?: string;
}

/** Spatial query parameters for GIS search */
export interface SpatialQuery {
  /** Search within this bounding box */
  bounds?: BoundingBox;
  /** Search within radius (meters) of a point */
  nearPoint?: Coordinate;
  radiusMeters?: number;
  /** Filter by district/taluka */
  district?: string;
  taluka?: string;
  village?: string;
  /** Filter by acquisition status */
  status?: 'not_acquired' | 'in_progress' | 'acquired';
}

/** Survey measurement record */
export interface SurveyMeasurement {
  surveyNumber: string;
  measurementDate: string;
  surveyorName: string;
  surveyorId: string;
  method: 'total_station' | 'dgps' | 'plane_table' | 'chain_survey';
  accuracy: 'high' | 'medium' | 'low';
  coordinates: Coordinate[];
  areaSqm: number;
  perimeterMeters: number;
  remarks?: string;
}
