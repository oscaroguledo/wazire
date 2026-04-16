/**
 * Frontend Configuration
 * Matches backend structure and provides environment-based settings
 */

/// <reference types="vite/client" />

export interface AppConfig {
  // App identification
  APP_NAME: string;
  ENV: 'development' | 'production' | 'test';
  DEBUG: boolean;

  // API Configuration
  API_BASE_URL: string;
  API_VERSION: string;

  // Authentication
  TOKEN_KEY: string;
  TOKEN_EXPIRE_SECONDS: number;

  // UI Configuration
  DEFAULT_PAGE_SIZE: number;
  MAX_PAGE_SIZE: number;
  PAGINATION_SIZES: number[];

  // Feature Flags
  ENABLE_ANALYTICS: boolean;
  ENABLE_ERROR_REPORTING: boolean;
  ENABLE_PERFORMANCE_MONITORING: boolean;

  // Timeouts
  API_TIMEOUT: number;
  UPLOAD_TIMEOUT: number;

  // File Upload
  MAX_FILE_SIZE: number; // in bytes
  ALLOWED_FILE_TYPES: string[];

  // Cache Configuration
  CACHE_TTL: number; // in seconds
  ENABLE_CACHE: boolean;

  // Theme
  DEFAULT_THEME: 'light' | 'dark' | 'system';
  PRIMARY_COLOR: string;

  // Routes
  ROUTES: {
    LOGIN: string;
    REGISTER: string;
    DASHBOARD: string;
    COURSES: string;
    EXAMS: string;
    SUBMISSIONS: string;
    PROFILE: string;
    SETTINGS: string;
  };
}

/**
 * Default configuration values
 */
const DEFAULT_CONFIG: AppConfig = {
  // App identification
  APP_NAME: 'wazire',
  ENV: 'development',
  DEBUG: true,

  // API Configuration
  API_BASE_URL: '/api/v1',
  API_VERSION: 'v1',

  // Authentication
  TOKEN_KEY: 'access_token',
  TOKEN_EXPIRE_SECONDS: 3600,

  // UI Configuration
  DEFAULT_PAGE_SIZE: 10,
  MAX_PAGE_SIZE: 100,
  PAGINATION_SIZES: [5, 10, 20, 50],

  // Feature Flags
  ENABLE_ANALYTICS: false,
  ENABLE_ERROR_REPORTING: false,
  ENABLE_PERFORMANCE_MONITORING: false,

  // Timeouts
  API_TIMEOUT: 30000, // 30 seconds
  UPLOAD_TIMEOUT: 300000, // 5 minutes

  // File Upload
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_FILE_TYPES: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png',
    'text/plain'
  ],

  // Cache Configuration
  CACHE_TTL: 300, // 5 minutes
  ENABLE_CACHE: true,

  // Theme
  DEFAULT_THEME: 'system',
  PRIMARY_COLOR: '#4F46E5', // royal-600

  // Routes
  ROUTES: {
    LOGIN: '/login',
    REGISTER: '/register',
    DASHBOARD: '/dashboard',
    COURSES: '/courses',
    EXAMS: '/exams',
    SUBMISSIONS: '/submissions',
    PROFILE: '/profile',
    SETTINGS: '/settings'
  }
};

/**
 * Load configuration from environment variables
 */
function loadConfig(): AppConfig {
  const config = { ...DEFAULT_CONFIG };

  // Type-safe environment variable access using Vite's ImportMetaEnv
  const env = import.meta.env as ImportMetaEnv;

  // Override with environment variables
  if (env.VITE_APP_NAME) {
    config.APP_NAME = env.VITE_APP_NAME;
  }
  
  if (env.VITE_ENV) {
    config.ENV = env.VITE_ENV as 'development' | 'production' | 'test';
  }
  
  if (env.VITE_DEBUG) {
    config.DEBUG = env.VITE_DEBUG === 'true';
  }

  if (env.VITE_API_BASE_URL) {
    config.API_BASE_URL = env.VITE_API_BASE_URL;
  }

  if (env.VITE_API_VERSION) {
    config.API_VERSION = env.VITE_API_VERSION;
  }

  if (env.VITE_TOKEN_KEY) {
    config.TOKEN_KEY = env.VITE_TOKEN_KEY;
  }

  if (env.VITE_TOKEN_EXPIRE_SECONDS) {
    config.TOKEN_EXPIRE_SECONDS = parseInt(env.VITE_TOKEN_EXPIRE_SECONDS);
  }

  if (env.VITE_DEFAULT_PAGE_SIZE) {
    config.DEFAULT_PAGE_SIZE = parseInt(env.VITE_DEFAULT_PAGE_SIZE);
  }

  if (env.VITE_MAX_PAGE_SIZE) {
    config.MAX_PAGE_SIZE = parseInt(env.VITE_MAX_PAGE_SIZE);
  }

  if (env.VITE_API_TIMEOUT) {
    config.API_TIMEOUT = parseInt(env.VITE_API_TIMEOUT);
  }

  if (env.VITE_UPLOAD_TIMEOUT) {
    config.UPLOAD_TIMEOUT = parseInt(env.VITE_UPLOAD_TIMEOUT);
  }

  if (env.VITE_MAX_FILE_SIZE) {
    config.MAX_FILE_SIZE = parseInt(env.VITE_MAX_FILE_SIZE);
  }

  if (env.VITE_ENABLE_ANALYTICS) {
    config.ENABLE_ANALYTICS = env.VITE_ENABLE_ANALYTICS === 'true';
  }

  if (env.VITE_ENABLE_ERROR_REPORTING) {
    config.ENABLE_ERROR_REPORTING = env.VITE_ENABLE_ERROR_REPORTING === 'true';
  }

  if (env.VITE_ENABLE_PERFORMANCE_MONITORING) {
    config.ENABLE_PERFORMANCE_MONITORING = env.VITE_ENABLE_PERFORMANCE_MONITORING === 'true';
  }

  if (env.VITE_CACHE_TTL) {
    config.CACHE_TTL = parseInt(env.VITE_CACHE_TTL);
  }

  if (env.VITE_ENABLE_CACHE) {
    config.ENABLE_CACHE = env.VITE_ENABLE_CACHE === 'true';
  }

  if (env.VITE_DEFAULT_THEME) {
    config.DEFAULT_THEME = env.VITE_DEFAULT_THEME as 'light' | 'dark' | 'system';
  }

  if (env.VITE_PRIMARY_COLOR) {
    config.PRIMARY_COLOR = env.VITE_PRIMARY_COLOR;
  }

  return config;
}

/**
 * Exported configuration instance
 */
export const config = loadConfig();

/**
 * Helper functions
 */
export const isDevelopment = () => config.ENV === 'development';
export const isProduction = () => config.ENV === 'production';
export const isTest = () => config.ENV === 'test';

export const getApiUrl = (path?: string) => {
  const baseUrl = config.API_BASE_URL.endsWith('/') 
    ? config.API_BASE_URL.slice(0, -1) 
    : config.API_BASE_URL;
  const cleanPath = path && path.startsWith('/') ? path.slice(1) : path || '';
  return `${baseUrl}/${cleanPath}`;
};

export const getAuthToken = () => {
  try {
    return localStorage.getItem(config.TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setAuthToken = (token: string) => {
  try {
    localStorage.setItem(config.TOKEN_KEY, token);
  } catch {
    // Ignore localStorage errors
  }
};

export const removeAuthToken = () => {
  try {
    localStorage.removeItem(config.TOKEN_KEY);
    // Also remove stored user and refresh token to ensure app state becomes unauthenticated
    try { localStorage.removeItem('wazire_user') } catch (err) {
      console.warn('Failed to remove wazire_user from localStorage:', err)
    }
    try { localStorage.removeItem('refresh_token') } catch (err) {
      console.warn('Failed to remove refresh_token from localStorage:', err)
    }
  } catch (err) {
    console.warn('Failed to remove auth token from localStorage:', err)
  }
};

export const isTokenExpired = () => {
  const token = getAuthToken();
  if (!token) return true;

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const now = Math.floor(Date.now() / 1000);
    return payload.exp < now;
  } catch {
    return true;
  }
};

/**
 * Validation helpers
 */
export const validateFileSize = (file: File) => {
  return file.size <= config.MAX_FILE_SIZE;
};

export const validateFileType = (file: File) => {
  return config.ALLOWED_FILE_TYPES.includes(file.type);
};

export const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Export configuration as default
 */
export default config;
