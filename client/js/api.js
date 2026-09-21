/**
 * API Client for Crop Insurance Backend Service
 */
const ApiClient = {
  /**
   * Ping backend health endpoint
   */
  async checkHealth() {
    const baseUrl = window.AppConfig.getApiBaseUrl();
    try {
      const response = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      const data = await response.json();
      return { ok: response.ok, status: response.status, data };
    } catch (err) {
      return { ok: false, error: err.message || 'Connection failed' };
    }
  },

  /**
   * Submit Claim with Multimodal Assessment
   * @param {Object} payload
   */
  async submitClaim(payload) {
    const baseUrl = window.AppConfig.getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/claims`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.message || `Server returned error ${response.status}`);
    }
    return result;
  },

  /**
   * Get Claim status by Claim ID
   * @param {string} claimId
   */
  async getClaim(claimId) {
    const baseUrl = window.AppConfig.getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/claims/${encodeURIComponent(claimId)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.message || `Claim not found (HTTP ${response.status})`);
    }
    return result;
  },

  /**
   * Fetch Audit Trail by Claim ID
   * @param {string} claimId
   */
  async getAuditTrail(claimId) {
    const baseUrl = window.AppConfig.getApiBaseUrl();
    try {
      const response = await fetch(`${baseUrl}/api/claims/${encodeURIComponent(claimId)}/audit`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      if (response.ok) {
        return await response.json();
      }
    } catch (e) {}

    // Fallback: extract auditLogs from getClaim
    try {
      const claimRes = await this.getClaim(claimId);
      return {
        success: true,
        data: claimRes.data?.auditLogs || []
      };
    } catch (err) {
      throw new Error(err.message || 'Audit trail not found');
    }
  },

  /**
   * Fetch recent claims
   * @param {number} limit
   */
  async listClaims(limit = 50) {
    const baseUrl = window.AppConfig.getApiBaseUrl();
    try {
      const response = await fetch(`${baseUrl}/api/claims?limit=${limit}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      if (response.ok) {
        const json = await response.json();
        const list = Array.isArray(json) ? json : (Array.isArray(json?.data) ? json.data : []);
        return { success: true, data: list };
      }
    } catch (e) {
      console.warn('Could not list claims:', e);
    }
    return { success: false, data: [] };
  },

  /**
   * Clear all historical claims
   */
  async clearClaims() {
    const baseUrl = window.AppConfig.getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/claims`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json' },
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.message || 'Failed to clear claims');
    }
    return result;
  },
};

window.ApiClient = ApiClient;
