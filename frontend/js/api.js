/**
 * api.js — All SkyAlert API calls in one place.
 *
 * Every function returns the parsed JSON response or throws an Error
 * with the server's detail message. No fetch() calls anywhere else.
 */

const BASE = "";  // Same origin — FastAPI serves both API and frontend.

/**
 * Internal helper: fetch with JSON body, throw on non-2xx.
 * @param {string} path
 * @param {RequestInit} options
 * @returns {Promise<any>}
 */
async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Unknown error");
  }
  // 204 No Content has no body
  if (res.status === 204) return null;
  return res.json();
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

/**
 * Register a new user.
 * @param {{ email: string, phone: string, whatsapp_enabled: boolean }} data
 * @returns {Promise<object>} UserResponse
 */
export async function createUser(data) {
  return request("/users/", { method: "POST", body: JSON.stringify(data) });
}

/**
 * Fetch a user by ID.
 * @param {string} userId
 * @returns {Promise<object>} UserResponse
 */
export async function getUser(userId) {
  return request(`/users/${userId}`);
}

// ---------------------------------------------------------------------------
// Searches
// ---------------------------------------------------------------------------

/**
 * Create a new flight price monitoring search.
 * @param {object} data  CreateSearchRequest fields
 * @returns {Promise<object>} SearchResponse
 */
export async function createSearch(data) {
  return request("/searches", { method: "POST", body: JSON.stringify(data) });
}

/**
 * Fetch all searches for a user.
 * @param {string} userId
 * @returns {Promise<object[]>} SearchResponse[]
 */
export async function getUserSearches(userId) {
  return request(`/users/${userId}/searches`);
}

/**
 * Deactivate (soft-delete) a search.
 * @param {string} searchId
 * @returns {Promise<null>}
 */
export async function deleteSearch(searchId) {
  return request(`/searches/${searchId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

/**
 * Fetch all alerts for a search.
 * @param {string} searchId
 * @returns {Promise<object[]>} AlertResponse[]
 */
export async function getSearchAlerts(searchId) {
  return request(`/searches/${searchId}/alerts`);
}

/**
 * Fetch a single alert by ID.
 * @param {string} alertId
 * @returns {Promise<object>} AlertResponse
 */
export async function getAlert(alertId) {
  return request(`/alerts/${alertId}`);
}

/**
 * Confirm an alert, optionally triggering automatic purchase.
 * @param {string} alertId
 * @param {string} userId
 * @param {boolean} triggerPurchase
 * @returns {Promise<object>} AlertResponse
 */
export async function confirmAlert(alertId, userId, triggerPurchase = false) {
  return request(`/alerts/${alertId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, trigger_purchase: triggerPurchase }),
  });
}
