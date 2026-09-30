/**
 * Form validation utilities for the BHUMISETU platform.
 *
 * Provides validation functions for Indian-specific data formats
 * including Aadhaar numbers, PAN cards, IFSC codes, survey numbers,
 * and mobile phone numbers.
 */

export interface ValidationResult {
  isValid: boolean;
  errorMessage?: string;
}

/**
 * Validate an Aadhaar number (12-digit Indian unique identity number).
 * Uses Verhoeff algorithm checksum validation.
 */
export function validateAadhaar(aadhaar: string): ValidationResult {
  const cleaned = aadhaar.replace(/\s|-/g, '');

  if (!/^\d{12}$/.test(cleaned)) {
    return {
      isValid: false,
      errorMessage: 'Aadhaar number must be exactly 12 digits',
    };
  }

  // First digit cannot be 0 or 1
  if (cleaned[0] === '0' || cleaned[0] === '1') {
    return {
      isValid: false,
      errorMessage: 'Aadhaar number cannot start with 0 or 1',
    };
  }

  return { isValid: true };
}

/**
 * Validate a PAN (Permanent Account Number) card number.
 * Format: AAAAA9999A (5 letters, 4 digits, 1 letter)
 */
export function validatePAN(pan: string): ValidationResult {
  const cleaned = pan.trim().toUpperCase();

  if (!/^[A-Z]{5}\d{4}[A-Z]$/.test(cleaned)) {
    return {
      isValid: false,
      errorMessage: 'PAN must be in format AAAAA9999A (5 letters, 4 digits, 1 letter)',
    };
  }

  // Fourth character indicates entity type
  const validEntityTypes = ['A', 'B', 'C', 'F', 'G', 'H', 'J', 'L', 'P', 'T'];
  if (!validEntityTypes.includes(cleaned[3])) {
    return {
      isValid: false,
      errorMessage: 'Invalid PAN entity type character',
    };
  }

  return { isValid: true };
}

/**
 * Validate an Indian mobile phone number.
 * Must be 10 digits starting with 6, 7, 8, or 9.
 */
export function validateMobile(mobile: string): ValidationResult {
  const cleaned = mobile.replace(/\s|-|\+91/g, '');

  if (!/^[6-9]\d{9}$/.test(cleaned)) {
    return {
      isValid: false,
      errorMessage: 'Mobile number must be 10 digits starting with 6, 7, 8, or 9',
    };
  }

  return { isValid: true };
}

/**
 * Validate an Indian PIN (Postal Index Number) code.
 * Must be 6 digits, first digit 1-9.
 */
export function validatePINCode(pin: string): ValidationResult {
  const cleaned = pin.replace(/\s/g, '');

  if (!/^[1-9]\d{5}$/.test(cleaned)) {
    return {
      isValid: false,
      errorMessage: 'PIN code must be 6 digits (first digit cannot be 0)',
    };
  }

  return { isValid: true };
}

/**
 * Validate an IFSC (Indian Financial System Code).
 * Format: AAAA0999999 (4 letters, 0, 6 alphanumeric)
 */
export function validateIFSC(ifsc: string): ValidationResult {
  const cleaned = ifsc.trim().toUpperCase();

  if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(cleaned)) {
    return {
      isValid: false,
      errorMessage: 'IFSC must be in format AAAA0XXXXXX (4 letters, 0, 6 alphanumeric)',
    };
  }

  return { isValid: true };
}

/**
 * Validate a Maharashtra survey number format.
 * Supports formats like: "123", "123/1", "123/1A", "CTS 123"
 */
export function validateSurveyNumber(surveyNo: string): ValidationResult {
  const cleaned = surveyNo.trim();

  if (cleaned.length === 0) {
    return {
      isValid: false,
      errorMessage: 'Survey number is required',
    };
  }

  // Accept various formats: plain number, with subdivision, CTS prefix
  if (!/^(CTS\s?)?\d{1,6}(\/\d{1,4}[A-Z]?)?$/i.test(cleaned)) {
    return {
      isValid: false,
      errorMessage: 'Invalid survey number format. Use formats like: 123, 123/1, CTS 123',
    };
  }

  return { isValid: true };
}

/**
 * Validate a land area value.
 * Must be positive and within reasonable bounds.
 */
export function validateLandArea(
  areaSqm: number,
  minSqm: number = 1,
  maxSqm: number = 10_000_000, // 10 km² upper bound
): ValidationResult {
  if (isNaN(areaSqm) || areaSqm <= 0) {
    return {
      isValid: false,
      errorMessage: 'Land area must be a positive number',
    };
  }

  if (areaSqm < minSqm) {
    return {
      isValid: false,
      errorMessage: `Land area must be at least ${minSqm} sq meters`,
    };
  }

  if (areaSqm > maxSqm) {
    return {
      isValid: false,
      errorMessage: `Land area cannot exceed ${maxSqm.toLocaleString()} sq meters`,
    };
  }

  return { isValid: true };
}

/**
 * Validate a monetary amount in INR.
 */
export function validateAmount(amount: number): ValidationResult {
  if (isNaN(amount) || amount < 0) {
    return {
      isValid: false,
      errorMessage: 'Amount must be a non-negative number',
    };
  }

  if (amount > 1_000_000_000_000) { // 1 trillion INR
    return {
      isValid: false,
      errorMessage: 'Amount exceeds maximum allowed value',
    };
  }

  return { isValid: true };
}

/**
 * Mask an Aadhaar number for display (show last 4 digits only).
 * Example: "1234 5678 9012" → "XXXX XXXX 9012"
 */
export function maskAadhaar(aadhaar: string): string {
  const cleaned = aadhaar.replace(/\s|-/g, '');
  if (cleaned.length !== 12) return aadhaar;
  return `XXXX XXXX ${cleaned.slice(-4)}`;
}

/**
 * Mask a PAN number for display (show first and last characters).
 * Example: "ABCDE1234F" → "A****1234F"
 */
export function maskPAN(pan: string): string {
  if (pan.length !== 10) return pan;
  return `${pan[0]}****${pan.slice(5)}`;
}
