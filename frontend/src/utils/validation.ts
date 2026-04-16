// Manual validation utilities for frontend forms
// Matches backend validation rules in core/utils/validation.py

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

// Email validation
export const validateEmail = (email: string): ValidationResult => {
  if (!email || email.trim() === '') {
    return { isValid: false, error: 'Email is required' };
  }

  const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  if (!emailPattern.test(email)) {
    return { isValid: false, error: 'Invalid email format' };
  }

  return { isValid: true };
};

// Password validation
export const validatePassword = (password: string): ValidationResult => {
  if (!password || password === '') {
    return { isValid: false, error: 'Password is required' };
  }

  if (password.length < 8) {
    return { isValid: false, error: 'Password must be at least 8 characters long' };
  }

  if (!/[A-Z]/.test(password)) {
    return { isValid: false, error: 'Password must contain at least one uppercase letter' };
  }

  if (!/[a-z]/.test(password)) {
    return { isValid: false, error: 'Password must contain at least one lowercase letter' };
  }

  if (!/[0-9]/.test(password)) {
    return { isValid: false, error: 'Password must contain at least one digit' };
  }

  return { isValid: true };
};

// Name validation
export const validateName = (name: string, fieldName: string = 'Name'): ValidationResult => {
  if (!name || name.trim() === '') {
    return { isValid: false, error: `${fieldName} is required` };
  }

  if (name.trim().length < 2) {
    return { isValid: false, error: `${fieldName} must be at least 2 characters long` };
  }

  if (name.length > 50) {
    return { isValid: false, error: `${fieldName} must not exceed 50 characters` };
  }

  return { isValid: true };
};

// Title validation (for exams, courses, etc.)
export const validateTitle = (title: string): ValidationResult => {
  if (!title || title.trim() === '') {
    return { isValid: false, error: 'Title is required' };
  }

  if (title.trim().length < 3) {
    return { isValid: false, error: 'Title must be at least 3 characters long' };
  }

  if (title.length > 200) {
    return { isValid: false, error: 'Title must not exceed 200 characters' };
  }

  return { isValid: true };
};

// Duration validation (in hours)
export const validateDuration = (duration: number): ValidationResult => {
  if (!duration || duration <= 0) {
    return { isValid: false, error: 'Duration must be greater than 0' };
  }

  if (duration > 24) {
    return { isValid: false, error: 'Duration must not exceed 24 hours' };
  }

  if (duration < 1) {
    return { isValid: false, error: 'Duration must be at least 1 hour' };
  }

  return { isValid: true };
};

// Marks validation
export const validateMarks = (marks: number, fieldName: string = 'Marks'): ValidationResult => {
  if (marks < 0) {
    return { isValid: false, error: `${fieldName} cannot be negative` };
  }

  if (marks > 1000) {
    return { isValid: false, error: `${fieldName} cannot exceed 1000` };
  }

  return { isValid: true };
};

// Max attempts validation
export const validateMaxAttempts = (maxAttempts: number): ValidationResult => {
  if (maxAttempts < 1) {
    return { isValid: false, error: 'Max attempts must be at least 1' };
  }

  if (maxAttempts > 10) {
    return { isValid: false, error: 'Max attempts cannot exceed 10' };
  }

  return { isValid: true };
};

// Status validation
export const validateExamStatus = (status: string): ValidationResult => {
  const validStatuses = ['not_started', 'in_progress', 'finished', 'draft'];
  if (!validStatuses.includes(status.toLowerCase())) {
    return { isValid: false, error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` };
  }

  return { isValid: true };
};

// Role validation
export const validateRole = (role: string): ValidationResult => {
  const validRoles = ['student', 'lecturer', 'admin', 'superadmin'];
  if (!validRoles.includes(role.toLowerCase())) {
    return { isValid: false, error: `Invalid role. Must be one of: ${validRoles.join(', ')}` };
  }

  return { isValid: true };
};

// Institution ID validation
export const validateInstitutionId = (institutionId: string): ValidationResult => {
  if (!institutionId || institutionId.trim() === '') {
    return { isValid: true }; // Optional field
  }

  if (institutionId.trim().length < 3) {
    return { isValid: false, error: 'Institution ID must be at least 3 characters long' };
  }

  if (institutionId.length > 50) {
    return { isValid: false, error: 'Institution ID must not exceed 50 characters' };
  }

  return { isValid: true };
};

// Phone number validation (basic)
export const validatePhoneNumber = (phone: string): ValidationResult => {
  if (!phone || phone.trim() === '') {
    return { isValid: true }; // Optional field
  }

  const cleaned = phone.replace(/[\s\-\(\)]/g, '');
  if (!/^\d{10,15}$/.test(cleaned)) {
    return { isValid: false, error: 'Invalid phone number format' };
  }

  return { isValid: true };
};

// UUID validation
export const validateUUID = (uuid: string): ValidationResult => {
  if (!uuid || uuid.trim() === '') {
    return { isValid: false, error: 'UUID is required' };
  }

  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidPattern.test(uuid)) {
    return { isValid: false, error: 'Invalid UUID format' };
  }

  return { isValid: true };
};

// Score validation (0-100)
export const validateScore = (score: number): ValidationResult => {
  if (score < 0) {
    return { isValid: false, error: 'Score cannot be negative' };
  }

  if (score > 100) {
    return { isValid: false, error: 'Score cannot exceed 100' };
  }

  return { isValid: true };
};

// Required field validation
export const validateRequired = (value: any, fieldName: string = 'Field'): ValidationResult => {
  if (value === null || value === undefined || value === '') {
    return { isValid: false, error: `${fieldName} is required` };
  }

  if (typeof value === 'string' && value.trim() === '') {
    return { isValid: false, error: `${fieldName} is required` };
  }

  return { isValid: true };
};

// URL validation
export const validateURL = (url: string): ValidationResult => {
  if (!url || url.trim() === '') {
    return { isValid: true }; // Optional field
  }

  try {
    new URL(url);
    return { isValid: true };
  } catch {
    return { isValid: false, error: 'Invalid URL format' };
  }
};

// HTML sanitization (basic)
export const sanitizeHTML = (html: string): ValidationResult => {
  if (!html || html.trim() === '') {
    return { isValid: true };
  }

  const dangerousTags = ['<script', '</script', '<iframe', '</iframe', '<object', '</object'];
  const lowerHtml = html.toLowerCase();

  for (const tag of dangerousTags) {
    if (lowerHtml.includes(tag)) {
      return { isValid: false, error: 'Invalid input: contains dangerous content' };
    }
  }

  return { isValid: true };
};

// Form validator - validates entire form object
export const validateForm = (formData: Record<string, any>, rules: Record<string, (value: any) => ValidationResult>): Record<string, ValidationResult> => {
  const results: Record<string, ValidationResult> = {};

  for (const [field, validator] of Object.entries(rules)) {
    results[field] = validator(formData[field]);
  }

  return results;
};

// Check if form has any errors
export const hasFormErrors = (validationResults: Record<string, ValidationResult>): boolean => {
  return Object.values(validationResults).some(result => !result.isValid);
};

// Get first error message from validation results
export const getFirstError = (validationResults: Record<string, ValidationResult>): string | null => {
  for (const result of Object.values(validationResults)) {
    if (!result.isValid && result.error) {
      return result.error;
    }
  }
  return null;
};
