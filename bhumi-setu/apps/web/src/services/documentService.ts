/**
 * Document management service for the BHUMISETU platform.
 * Handles document upload, retrieval, OCR, and verification.
 */

import type { DocumentMeta, OCRResult, DocumentVerification } from '../types/document';

const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Upload a document for a case.
 */
export async function uploadDocument(
  caseId: string,
  file: File,
  documentType: string,
  description?: string,
): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('case_id', caseId);
  formData.append('document_type', documentType);
  if (description) formData.append('description', description);

  const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
    },
    body: formData,
  });

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Get documents for a case.
 */
export async function getDocumentsByCase(
  caseId: string,
): Promise<DocumentMeta[]> {
  const response = await fetch(
    `${API_BASE}/api/v1/cases/${caseId}/documents`,
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
 * Get OCR extraction results for a document.
 */
export async function getOCRResults(
  documentId: string,
): Promise<OCRResult> {
  const response = await fetch(
    `${API_BASE}/api/v1/documents/${documentId}/ocr`,
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
 * Trigger OCR processing for a document.
 */
export async function triggerOCR(
  documentId: string,
  language: 'en' | 'hi' | 'mr' = 'en',
): Promise<{ taskId: string; status: string }> {
  const response = await fetch(
    `${API_BASE}/api/v1/documents/${documentId}/ocr`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ language }),
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Submit document verification result.
 */
export async function verifyDocument(
  documentId: string,
  isAuthentic: boolean,
  method: 'manual' | 'ai_assisted' | 'cross_reference',
  notes?: string,
): Promise<DocumentVerification> {
  const response = await fetch(
    `${API_BASE}/api/v1/documents/${documentId}/verify`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_authentic: isAuthentic, method, notes }),
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Download a document file.
 */
export async function downloadDocument(documentId: string): Promise<Blob> {
  const response = await fetch(
    `${API_BASE}/api/v1/documents/${documentId}/download`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.blob();
}

/**
 * Delete a document (soft delete).
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/v1/documents/${documentId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
}
