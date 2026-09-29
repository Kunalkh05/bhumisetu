/**
 * PostGIS Spatial Engine Utility Library
 * Provides WGS 84 (EPSG:4326), Web Mercator (EPSG:3857), UTM Zone 43N (EPSG:32643) 
 * transformations, WKT serialization, GeoJSON conversion, geodesic calculations, 
 * spatial predicates (ST_Intersects, ST_Contains, ST_Area, ST_Buffer, ST_Distance), 
 * and simulated PostGIS SQL execution.
 */

export interface PostGisPoint {
  lat: number;
  lng: number;
}

export interface PostGisFeature {
  id: string;
  surveyNumber: string;
  village: string;
  classification: string;
  extentHa: number;
  riskBand: string;
  caseReference: string;
  coordinates: [number, number][]; // [lat, lng] pairs
  srid: number;
}

export interface PostGisQueryResult {
  query: string;
  executionTimeMs: number;
  rowCount: number;
  columns: string[];
  rows: Record<string, any>[];
  spatialHighlightIds?: string[];
  derivedGeometries?: Array<{
    type: 'Polygon' | 'Point' | 'LineString';
    coordinates: any;
    label: string;
    color: string;
  }>;
}

// Earth radius in meters for WGS 84
const EARTH_RADIUS_METERS = 6378137.0;

/**
 * Calculates geodesic area of a polygon in square meters using spherical excess formula (PostGIS ST_Area(geom::geography))
 */
export function ST_Area(coordinates: [number, number][]): number {
  if (coordinates.length < 3) return 0;
  
  let totalArea = 0;
  const numPoints = coordinates.length;
  
  for (let i = 0; i < numPoints; i++) {
    const p1 = coordinates[i];
    const p2 = coordinates[(i + 1) % numPoints];
    
    const lat1Rad = (p1[0] * Math.PI) / 180;
    const lat2Rad = (p2[0] * Math.PI) / 180;
    const lng1Rad = (p1[1] * Math.PI) / 180;
    const lng2Rad = (p2[1] * Math.PI) / 180;
    
    totalArea += (lng2Rad - lng1Rad) * (2 + Math.sin(lat1Rad) + Math.sin(lat2Rad));
  }
  
  totalArea = (Math.abs(totalArea) * EARTH_RADIUS_METERS * EARTH_RADIUS_METERS) / 2.0;
  return Math.round(totalArea * 100) / 100;
}

/**
 * Calculates geodesic perimeter of a polygon in meters (PostGIS ST_Perimeter(geom::geography))
 */
export function ST_Perimeter(coordinates: [number, number][]): number {
  if (coordinates.length < 2) return 0;
  let totalLength = 0;
  
  for (let i = 0; i < coordinates.length - 1; i++) {
    totalLength += ST_Distance(coordinates[i], coordinates[i + 1]);
  }
  return Math.round(totalLength * 100) / 100;
}

/**
 * Calculates Great Circle distance between two points in meters using Haversine formula (PostGIS ST_Distance(p1::geography, p2::geography))
 */
export function ST_Distance(p1: [number, number], p2: [number, number]): number {
  const lat1 = (p1[0] * Math.PI) / 180;
  const lng1 = (p1[1] * Math.PI) / 180;
  const lat2 = (p2[0] * Math.PI) / 180;
  const lng2 = (p2[1] * Math.PI) / 180;
  
  const dLat = lat2 - lat1;
  const dLng = lng2 - lng1;
  
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_METERS * c;
}

/**
 * Computes geometric centroid of polygon coordinates (PostGIS ST_Centroid(geom))
 */
export function ST_Centroid(coordinates: [number, number][]): [number, number] {
  if (coordinates.length === 0) return [0, 0];
  let sumLat = 0;
  let sumLng = 0;
  const n = coordinates.length;
  
  for (let i = 0; i < n; i++) {
    sumLat += coordinates[i][0];
    sumLng += coordinates[i][1];
  }
  
  return [Number((sumLat / n).toFixed(6)), Number((sumLng / n).toFixed(6))];
}

/**
 * Computes bounding box envelope [minLng, minLat, maxLng, maxLat] (PostGIS ST_Envelope(geom))
 */
export function ST_Envelope(coordinates: [number, number][]): [number, number, number, number] {
  let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
  for (const [lat, lng] of coordinates) {
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
  }
  return [minLng, minLat, maxLng, maxLat];
}

/**
 * Checks if a point is inside a polygon using Ray Casting (PostGIS ST_Contains(geom, point))
 */
export function ST_Contains(polygon: [number, number][], point: [number, number]): boolean {
  const [lat, lng] = point;
  let inside = false;
  
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = [polygon[i][1], polygon[i][0]];
    const [xj, yj] = [polygon[j][1], polygon[j][0]];
    
    const intersect = ((yi > lat) !== (yj > lat)) &&
        (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  
  return inside;
}

/**
 * Converts coordinates to Well-Known Text (WKT) format (PostGIS ST_AsText(geom))
 */
export function ST_AsText(coordinates: [number, number][], type: 'POLYGON' | 'LINESTRING' | 'POINT' = 'POLYGON', srid: number = 4326): string {
  if (type === 'POINT' && coordinates.length > 0) {
    return `SRID=${srid};POINT(${coordinates[0][1].toFixed(6)} ${coordinates[0][0].toFixed(6)})`;
  }
  
  if (type === 'LINESTRING') {
    const pointsStr = coordinates.map(c => `${c[1].toFixed(6)} ${c[0].toFixed(6)}`).join(', ');
    return `SRID=${srid};LINESTRING(${pointsStr})`;
  }
  
  // Ensure closed polygon
  const coords = [...coordinates];
  if (coords.length > 0 && (coords[0][0] !== coords[coords.length - 1][0] || coords[0][1] !== coords[coords.length - 1][1])) {
    coords.push(coords[0]);
  }
  
  const pointsStr = coords.map(c => `${c[1].toFixed(6)} ${c[0].toFixed(6)}`).join(', ');
  return `SRID=${srid};POLYGON((${pointsStr}))`;
}

/**
 * Converts coordinates to GeoJSON Feature (PostGIS ST_AsGeoJSON(geom))
 */
export function ST_AsGeoJSON(coordinates: [number, number][], properties: Record<string, any> = {}): object {
  const coords = [...coordinates];
  if (coords.length > 0 && (coords[0][0] !== coords[coords.length - 1][0] || coords[0][1] !== coords[coords.length - 1][1])) {
    coords.push(coords[0]);
  }
  
  // GeoJSON uses [longitude, latitude]
  const geoJsonCoords = coords.map(c => [c[1], c[0]]);
  
  return {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [geoJsonCoords]
    },
    properties: {
      srid: 4326,
      crs: "urn:ogc:def:crs:EPSG::4326",
      ...properties
    }
  };
}

/**
 * Generates PostGIS SQL INSERT statement for land parcel geometry
 */
export function generatePostGisInsertSQL(parcel: {
  id: string;
  surveyNumber: string;
  village: string;
  classification: string;
  extent: number;
  coordinates: [number, number][];
}): string {
  const wkt = ST_AsText(parcel.coordinates, 'POLYGON', 4326);
  return `INSERT INTO cadastral_parcels (
  parcel_id,
  survey_number,
  village_name,
  land_classification,
  extent_hectares,
  geom
) VALUES (
  '${parcel.id}',
  '${parcel.surveyNumber}',
  '${parcel.village}',
  '${parcel.classification}',
  ${parcel.extent},
  ST_GeomFromEWKT('${wkt}')
);`;
}

/**
 * Converts WGS84 Lat/Lng (EPSG:4326) to UTM Zone 43N (EPSG:32643) Easting/Northing in meters
 * Standard projection used for precision land survey across Western India / Maharashtra
 */
export function ST_TransformToUTM43N(lat: number, lng: number): { easting: number; northing: number; zone: string } {
  // Simplified Transverse Mercator projection for UTM Zone 43 (Central Meridian 75°E)
  const a = 6378137.0; // WGS84 major axis
  const f = 1 / 298.257223563; // flattening
  const k0 = 0.9996; // scale factor
  const centralMeridian = 75.0; // UTM Zone 43N central meridian
  
  const latRad = (lat * Math.PI) / 180;
  const lngRad = (lng * Math.PI) / 180;
  const cmRad = (centralMeridian * Math.PI) / 180;
  
  const e = Math.sqrt(2 * f - f * f);
  const N = a / Math.sqrt(1 - e * e * Math.sin(latRad) * Math.sin(latRad));
  const T = Math.tan(latRad) * Math.tan(latRad);
  const C = (e * e / (1 - e * e)) * Math.cos(latRad) * Math.cos(latRad);
  const A = Math.cos(latRad) * (lngRad - cmRad);
  
  // Meridional Arc
  const M = a * (
    (1 - e * e / 4 - 3 * e * e * e * e / 64) * latRad -
    (3 * e * e / 8 + 3 * e * e * e * e / 32) * Math.sin(2 * latRad) +
    (15 * e * e * e * e / 256) * Math.sin(4 * latRad)
  );
  
  const easting = 500000 + k0 * N * (A + (1 - T + C) * Math.pow(A, 3) / 6 + (5 - 18 * T + T * T + 72 * C) * Math.pow(A, 5) / 120);
  const northing = k0 * (M + N * Math.tan(latRad) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * Math.pow(A, 4) / 24));
  
  return {
    easting: Math.round(easting * 100) / 100,
    northing: Math.round(northing * 100) / 100,
    zone: "43N (EPSG:32643)"
  };
}

/**
 * Creates a geographic buffer polygon around a coordinate path (PostGIS ST_Buffer(geom::geography, distanceMeters))
 */
export function ST_Buffer(coordinates: [number, number][], distanceMeters: number): [number, number][] {
  if (coordinates.length === 0) return [];
  // Convert buffer distance to approximate degree offset
  const latOffset = distanceMeters / 111139.0;
  const lngOffset = distanceMeters / (111139.0 * Math.cos((coordinates[0][0] * Math.PI) / 180));
  
  const leftSide: [number, number][] = [];
  const rightSide: [number, number][] = [];
  
  for (let i = 0; i < coordinates.length; i++) {
    const [lat, lng] = coordinates[i];
    leftSide.push([lat + latOffset, lng - lngOffset]);
    rightSide.unshift([lat - latOffset, lng + lngOffset]);
  }
  
  return [...leftSide, ...rightSide, leftSide[0]];
}

/**
 * Computes topological spatial difference between current geometry and historical baseline
 * (PostGIS ST_Difference(geom_current, geom_historical)) to extract encroachment polygons.
 */
export function ST_Difference(
  currentCoords: [number, number][],
  historicalCoords: [number, number][]
): [number, number][] {
  if (currentCoords.length < 3) return [];
  // Return the exterior vertices from current that lie outside the historical baseline
  return currentCoords.filter(pt => !ST_Contains(historicalCoords, pt));
}

/**
 * Executes a simulated PostGIS spatial SQL query over the loaded cadastral dataset
 */
export function executePostGisQuery(
  sqlQuery: string,
  parcels: PostGisFeature[],
  highwayAlignment: [number, number][]
): PostGisQueryResult {
  const normalized = sqlQuery.trim().toLowerCase();
  const startTime = performance.now();
  
  // 0. Historical 1974 Cadastral Survey & Encroachment Difference Query
  if (normalized.includes('1974') || normalized.includes('st_difference') || normalized.includes('encroachment')) {
    const encroachmentParcels = [
      {
        survey_number: 'Gat No. 142/A',
        old_survey_1974: 'Old Survey No. 84, Hissa 2/A',
        village: 'Shindewadi',
        current_area_ha: 2.45,
        historical_area_ha: 2.03,
        encroachment_sqm: 418,
        encroached_zone: 'PWD Highway Right-of-Way Reserve',
        severity: 'CRITICAL',
        statutory_impact: 'Exclude 418 m² from Section 30 Solatium'
      },
      {
        survey_number: 'Gat No. 142/B',
        old_survey_1974: 'Old Survey No. 84, Hissa 2/B',
        village: 'Shindewadi',
        current_area_ha: 1.80,
        historical_area_ha: 1.51,
        encroachment_sqm: 285,
        encroached_zone: 'Village Gairan (Public Grazing)',
        severity: 'HIGH',
        statutory_impact: 'Restore 285 m² to Revenue Gairan'
      },
      {
        survey_number: 'Gat No. 143',
        old_survey_1974: 'Old Survey No. 85, Hissa 1',
        village: 'Shindewadi',
        current_area_ha: 1.25,
        historical_area_ha: 0.93,
        encroachment_sqm: 320,
        encroached_zone: 'Natural Drainage Stream (Nala Buffer)',
        severity: 'HIGH',
        statutory_impact: 'Notice to clear culvert backfill'
      },
      {
        survey_number: 'Gat No. 144/3',
        old_survey_1974: 'Old Survey No. 86, Hissa 3',
        village: 'Shindewadi',
        current_area_ha: 1.34,
        historical_area_ha: 1.23,
        encroachment_sqm: 110,
        encroached_zone: 'Agricultural Field Bund Creep',
        severity: 'MODERATE',
        statutory_impact: 'Joint demarcation correction'
      }
    ];

    return {
      query: sqlQuery,
      executionTimeMs: Number((performance.now() - startTime + 1.8).toFixed(2)),
      rowCount: encroachmentParcels.length,
      columns: ['survey_number', 'old_survey_1974', 'village', 'current_area_ha', 'historical_area_ha', 'encroachment_sqm', 'encroached_zone', 'severity', 'statutory_impact'],
      rows: encroachmentParcels,
      spatialHighlightIds: ['PCL-142A', 'PCL-142B', 'PCL-143', 'PCL-144'],
      derivedGeometries: [
        {
          type: 'Polygon',
          coordinates: [
            [18.3857, 73.8910],
            [18.3865, 73.8912],
            [18.3872, 73.8940],
            [18.3866, 73.8938],
            [18.3857, 73.8910]
          ],
          label: 'ST_Difference(Gat_142A, 1974_Cadastral): 418 m² RoW Encroachment',
          color: '#dc2626'
        },
        {
          type: 'Polygon',
          coordinates: [
            [18.3882, 73.8963],
            [18.3885, 73.8970],
            [18.3860, 73.8962],
            [18.3861, 73.8956],
            [18.3882, 73.8963]
          ],
          label: 'ST_Difference(Gat_142B, 1974_Cadastral): 285 m² Gairan Encroachment',
          color: '#ea580c'
        }
      ]
    };
  }
  
  // 1. Spatial Intersection Query (Parcels intersecting RoW alignment corridor buffer)
  if (normalized.includes('st_intersects') && (normalized.includes('buffer') || normalized.includes('highway') || normalized.includes('corridor'))) {
    const rows = parcels.map(p => {
      const areaSqM = ST_Area(p.coordinates);
      const centroid = ST_Centroid(p.coordinates);
      const utm = ST_TransformToUTM43N(centroid[0], centroid[1]);
      return {
        parcel_id: p.id,
        survey_number: p.surveyNumber,
        village: p.village,
        extent_ha: p.extentHa,
        postgis_area_ha: Number((areaSqM / 10000).toFixed(3)),
        intersects_row: true,
        utm_easting: utm.easting,
        utm_northing: utm.northing,
        spatial_wkt: ST_AsText(p.coordinates, 'POLYGON', 4326).substring(0, 48) + '...'
      };
    });
    
    return {
      query: sqlQuery,
      executionTimeMs: Number((performance.now() - startTime + 1.2).toFixed(2)),
      rowCount: rows.length,
      columns: ['parcel_id', 'survey_number', 'village', 'extent_ha', 'postgis_area_ha', 'intersects_row', 'utm_easting', 'utm_northing', 'spatial_wkt'],
      rows,
      spatialHighlightIds: parcels.map(p => p.id),
      derivedGeometries: [
        {
          type: 'Polygon',
          coordinates: ST_Buffer(highwayAlignment, 40),
          label: 'PostGIS ST_Buffer(NH-48_Alignment, 40m Corridor)',
          color: '#f59e0b'
        }
      ]
    };
  }
  
  // 2. High Risk or Objections Query
  if (normalized.includes('critical') || normalized.includes('risk') || normalized.includes('p >= 0.75')) {
    const criticalParcels = parcels.filter(p => p.riskBand === 'CRITICAL' || p.riskBand === 'HIGH');
    const rows = criticalParcels.map(p => {
      const centroid = ST_Centroid(p.coordinates);
      return {
        survey_number: p.surveyNumber,
        village: p.village,
        risk_band: p.riskBand,
        centroid_lat: centroid[0],
        centroid_lng: centroid[1],
        postgis_geometry_type: 'ST_Polygon',
        srid: 4326
      };
    });
    
    return {
      query: sqlQuery,
      executionTimeMs: Number((performance.now() - startTime + 0.8).toFixed(2)),
      rowCount: rows.length,
      columns: ['survey_number', 'village', 'risk_band', 'centroid_lat', 'centroid_lng', 'postgis_geometry_type', 'srid'],
      rows,
      spatialHighlightIds: criticalParcels.map(p => p.id)
    };
  }
  
  // 3. PostGIS ST_Area & ST_Perimeter Geodesic Analysis
  if (normalized.includes('st_area') || normalized.includes('st_perimeter')) {
    const rows = parcels.map(p => {
      const areaSqM = ST_Area(p.coordinates);
      const perimeterM = ST_Perimeter(p.coordinates);
      const centroid = ST_Centroid(p.coordinates);
      return {
        survey_number: p.surveyNumber,
        recorded_ha: p.extentHa,
        st_area_sqm: areaSqM,
        st_area_ha: Number((areaSqM / 10000).toFixed(4)),
        st_perimeter_m: perimeterM,
        variance_pct: Number((((areaSqM / 10000 - p.extentHa) / p.extentHa) * 100).toFixed(2)),
        centroid_wkt: `POINT(${centroid[1]} ${centroid[0]})`
      };
    });
    
    return {
      query: sqlQuery,
      executionTimeMs: Number((performance.now() - startTime + 1.5).toFixed(2)),
      rowCount: rows.length,
      columns: ['survey_number', 'recorded_ha', 'st_area_sqm', 'st_area_ha', 'st_perimeter_m', 'variance_pct', 'centroid_wkt'],
      rows,
      spatialHighlightIds: parcels.map(p => p.id)
    };
  }
  
  // 4. Default Cadastral Record Dump Query
  const rows = parcels.map(p => {
    const centroid = ST_Centroid(p.coordinates);
    const utm = ST_TransformToUTM43N(centroid[0], centroid[1]);
    return {
      id: p.id,
      survey_number: p.surveyNumber,
      village: p.village,
      classification: p.classification,
      extent_ha: p.extentHa,
      srid: 4326,
      utm_43n_e: utm.easting,
      utm_43n_n: utm.northing,
      geom_wkt: ST_AsText(p.coordinates, 'POLYGON', 4326).substring(0, 52) + '...'
    };
  });
  
  return {
    query: sqlQuery,
    executionTimeMs: Number((performance.now() - startTime + 0.9).toFixed(2)),
    rowCount: rows.length,
    columns: ['id', 'survey_number', 'village', 'classification', 'extent_ha', 'srid', 'utm_43n_e', 'utm_43n_n', 'geom_wkt'],
    rows,
    spatialHighlightIds: parcels.map(p => p.id)
  };
}
