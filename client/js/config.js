/**
 * Application Configuration
 */
const CONFIG_KEYS = {
  API_BASE_URL: 'crop_insurance_api_url',
};

const DEFAULT_CONFIG = {
  API_BASE_URL: (typeof window !== 'undefined' && window.location && window.location.port === '8000') ? '' : 'http://localhost:8000',
};

/**
 * Get configured backend API base URL
 */
function getApiBaseUrl() {
  return localStorage.getItem(CONFIG_KEYS.API_BASE_URL) || DEFAULT_CONFIG.API_BASE_URL;
}

/**
 * Update backend API base URL
 */
function setApiBaseUrl(url) {
  let cleanUrl = (url || '').trim();
  if (cleanUrl.endsWith('/')) {
    cleanUrl = cleanUrl.slice(0, -1);
  }
  if (!cleanUrl) {
    cleanUrl = DEFAULT_CONFIG.API_BASE_URL;
  }
  localStorage.setItem(CONFIG_KEYS.API_BASE_URL, cleanUrl);
  return cleanUrl;
}

// Export to window for global access
window.AppConfig = {
  getApiBaseUrl,
  setApiBaseUrl,
  DEFAULT_CONFIG,
};
