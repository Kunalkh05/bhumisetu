/**
 * Document-related type definitions for the BHUMISETU platform.
 */

/** Document types used in land acquisition proceedings */
export type DocumentType =
  | 'section_4_notification'     // Preliminary notification (old act)
  | 'section_11_notification'    // Preliminary notification (RFCTLARR)
  | 'section_15_hearing'         // Hearing of objections
  | 'section_19_declaration'     // Declaration of acquisition
  | 'section_23_award'           // Award
  | 'section_28_taking_possession' // Taking possession
  | 'sia_report'                 // Social Impact Assessment
  | 'survey_report'              // Land survey report
  | 'valuation_report'           // Market valuation report
  | '7_12_extract'               // 7/12 extract (satbara utara)
  | '8a_extract'                 // 8A extract (khata utara)
  | 'mutation_entry'             // Mutation entry
  | 'encumbrance_certificate'    // Encumbrance certificate
  | 'ferfar_patrak'              // Ferfar (mutation register)
  | 'court_order'                // Court order / decree
  | 'objection_letter'           // Citizen objection
  | 'consent_letter'             // Citizen consent
  | 'title_deed'                 // Title deed / sale deed
  | 'photograph'                 // Site photographs
  | 'map'                        // Map / layout
  | 'other';

/** Document processing status */
export type DocumentStatus =
  | 'uploaded'
  | 'scanning'
  | 'ocr_processing'
  | 'ocr_complete'
  | 'verified'
  | 'rejected'
  | 'archived';

/** OCR confidence levels */
export type OCRConfidence = 'high' | 'medium' | 'low' | 'failed';

/** Document metadata */
export interface DocumentMeta {
  id: string;
  caseId: string;
  fileName: string;
  originalFileName: string;
  fileSize: number;
  mimeType: string;
  documentType: DocumentType;
  status: DocumentStatus;
  uploadedBy: string;
  uploadedAt: string;
  verifiedBy?: string;
  verifiedAt?: string;
  description?: string;
  pageCount?: number;
  language?: 'en' | 'hi' | 'mr';
}

/** OCR extraction result */
export interface OCRResult {
  documentId: string;
  extractedText: string;
  confidence: OCRConfidence;
  overallScore: number;
  fieldExtractions: OCRFieldExtraction[];
  processedAt: string;
  processingDurationMs: number;
}

/** Individual field extraction from OCR */
export interface OCRFieldExtraction {
  fieldName: string;
  extractedValue: string;
  confidence: number;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
    page: number;
  };
}

/** Document verification result */
export interface DocumentVerification {
  documentId: string;
  isAuthentic: boolean;
  verificationMethod: 'manual' | 'ai_assisted' | 'cross_reference';
  verifiedBy: string;
  verifiedAt: string;
  notes?: string;
  crossReferencedWith?: string[];
}
