/**
 * GIS / Map service for the BHUMISETU platform.
 * Handles API calls for geospatial data and parcel boundaries.
 */

import type {
  ParcelFeatureCollection,
  SpatialQuery,
  SurveyMeasurement,
  MapMarker,
} from '../types/gis';

const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Fetch parcel boundaries within a bounding box.
 */
export async function getParcelsByBounds(
  north: number,
  south: number,
  east: number,
  west: number,
): Promise<ParcelFeatureCollection> {
  const params = new URLSearchParams({
    north: String(north),
    south: String(south),
    east: String(east),
    west: String(west),
  });

  const response = await fetch(
    `${API_BASE}/api/v1/gis/parcels?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Search parcels near a point with given radius.
 */
export async function searchParcelsNearPoint(
  latitude: number,
  longitude: number,
  radiusMeters: number = 1000,
): Promise<ParcelFeatureCollection> {
  const params = new URLSearchParams({
    lat: String(latitude),
    lng: String(longitude),
    radius: String(radiusMeters),
  });

  const response = await fetch(
    `${API_BASE}/api/v1/gis/parcels/nearby?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Get parcel boundary by survey number.
 */
export async function getParcelBySurveyNumber(
  surveyNumber: string,
  village: string,
  taluka: string,
  district: string,
): Promise<ParcelFeatureCollection> {
  const params = new URLSearchParams({
    survey_number: surveyNumber,
    village,
    taluka,
    district,
  });

  const response = await fetch(
    `${API_BASE}/api/v1/gis/parcels/search?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Get survey measurement records for a parcel.
 */
export async function getSurveyMeasurements(
  parcelId: string,
): Promise<SurveyMeasurement[]> {
  const response = await fetch(
    `${API_BASE}/api/v1/gis/parcels/${parcelId}/measurements`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Get map markers for acquisition-related locations.
 */
export async function getAcquisitionMarkers(
  district?: string,
  status?: string,
): Promise<MapMarker[]> {
  const params = new URLSearchParams();
  if (district) params.set('district', district);
  if (status) params.set('status', status);

  const response = await fetch(
    `${API_BASE}/api/v1/gis/markers?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Calculate area of a polygon from coordinates.
 * Uses the Shoelace formula for geodesic approximation.
 */
export function calculatePolygonArea(coordinates: [number, number][]): number {
  if (coordinates.length < 3) return 0;

  let area = 0;
  const n = coordinates.length;

  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    // Convert to approximate meters using latitude correction
    const lat1 = coordinates[i][1] * (Math.PI / 180);
    const lat2 = coordinates[j][1] * (Math.PI / 180);
    const lng1 = coordinates[i][0] * (Math.PI / 180);
    const lng2 = coordinates[j][0] * (Math.PI / 180);

    area += lng1 * Math.sin(lat2) - lng2 * Math.sin(lat1);
  }

  // Earth's radius squared × |area| / 2
  const R = 6371000; // meters
  return Math.abs(area) * R * R / 2;
}
