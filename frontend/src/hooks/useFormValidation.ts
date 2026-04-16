import { useState, useCallback } from 'react';
import { ValidationResult, validateForm, hasFormErrors } from '@/utils/validation';

interface UseFormValidationOptions<T extends Record<string, unknown> = Record<string, unknown>> {
  initialValues?: T;
  validationRules?: Record<string, (value: unknown) => ValidationResult>;
  onSubmit?: (data: T) => void | Promise<void>;
}

interface UseFormValidationReturn<T extends Record<string, unknown> = Record<string, unknown>> {
  values: T;
  errors: Record<string, string | null>;
  touched: Record<string, boolean>;
  isValid: boolean;
  handleChange: (field: string, value: unknown) => void;
  handleBlur: (field: string) => void;
  handleSubmit: (e?: React.FormEvent) => void;
  resetForm: () => void;
  setFieldValue: (field: string, value: unknown) => void;
  setError: (field: string, error: string | null) => void;
  clearError: (field: string) => void;
  validateField: (field: string, value: unknown) => ValidationResult;
  validateAll: () => boolean;
}

export function useFormValidation<T extends Record<string, unknown> = Record<string, unknown>>(options: UseFormValidationOptions<T> = {}): UseFormValidationReturn<T> {
  const { initialValues = {} as T, validationRules = {}, onSubmit } = options;

  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateField = useCallback((field: string, value: unknown): ValidationResult => {
    if (validationRules[field]) {
      return validationRules[field](value);
    }
    return { isValid: true };
  }, [validationRules]);

  const handleChange = useCallback((field: string, value: unknown) => {
    setValues(prev => ({ ...prev, [field]: value }) as T);

    // Validate field if it's already touched
    if (touched[field] && validationRules[field]) {
      const result = validateField(field, value);
      setErrors(prev => ({
        ...prev,
        [field]: result.error || null
      }));
    }
  }, [touched, validationRules, validateField]);

  const handleBlur = useCallback((field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }));

    if (validationRules[field]) {
      const result = validateField(field, (values as Record<string, unknown>)[field]);
      setErrors(prev => ({
        ...prev,
        [field]: result.error || null
      }));
    }
  }, [validationRules, values, validateField]);

  const validateAll = useCallback((): boolean => {
    const validationResults = validateForm(values as Record<string, unknown>, validationRules);
    const newErrors: Record<string, string | null> = {};

    for (const [field, result] of Object.entries(validationResults)) {
      newErrors[field] = result.error || null;
    }

    setErrors(newErrors);
    setTouched(Object.keys(values as Record<string, unknown>).reduce((acc, field) => ({ ...acc, [field]: true }), {}));

    return !hasFormErrors(validationResults);
  }, [values, validationRules]);

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }

    const isValid = validateAll();

    if (isValid && onSubmit) {
      await onSubmit(values);
    }
  }, [validateAll, onSubmit, values]);

  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  const setFieldValue = useCallback((field: string, value: unknown) => {
    setValues(prev => ({ ...prev, [field]: value }) as T);
  }, []);

  const setError = useCallback((field: string, error: string | null) => {
    setErrors(prev => ({ ...prev, [field]: error }));
  }, []);

  const clearError = useCallback((field: string) => {
    setErrors(prev => ({ ...prev, [field]: null }));
  }, []);

  const isValid = !hasFormErrors(
    Object.keys(values as Record<string, unknown>).reduce((acc, field) => {
      if (validationRules[field]) {
        acc[field] = validationRules[field]((values as Record<string, unknown>)[field]);
      }
      return acc;
    }, {} as Record<string, ValidationResult>)
  );

  return {
    values,
    errors,
    touched,
    isValid,
    handleChange,
    handleBlur,
    handleSubmit,
    resetForm,
    setFieldValue,
    setError,
    clearError,
    validateField,
    validateAll,
  };
}
