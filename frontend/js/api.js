/**
 * api.js — All SkyAlert API calls in one place.
 *
 * Every function returns the parsed JSON response or throws an Error
 * with the server's detail message. No fetch() calls anywhere else.
 */

const BASE = "";  // Same origin — FastAPI serves both API and frontend.

// ---------------------------------------------------------------------------
// Token helpers
// ---------------------------------------------------------------------------

function getToken() {
  return localStorage.getItem("skyalert_token");
}

export function setToken(token) {
  localStorage.setItem("skyalert_token", token);
}

/**
 * Internal helper: fetch with JSON body, throw on non-2xx.
 * Injects Authorization header when a token is stored.
 * @param {string} path
 * @param {RequestInit} options
 * @returns {Promise<any>}
 */
async function request(path, options = {}) {
  const token = getToken();
  const authHeader = token ? { "Authorization": `Bearer ${token}` } : {};

  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json", ...authHeader, ...options.headers },
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
 * Fetch a search by ID.
 * @param {string} searchId
 * @returns {Promise<object>} SearchResponse
 */
export async function getSearch(searchId) {
  return request(`/searches/${searchId}`);
}

/**
 * Create a new flight price monitoring search.
 * @param {object} data  CreateSearchRequest fields (no user_id — taken from token)
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
// Auth
// ---------------------------------------------------------------------------

/**
 * Request a magic-link login email.
 * @param {string} email
 * @returns {Promise<{message: string}>}
 */
export async function requestMagicLink(email) {
  return request("/auth/magic-link", { method: "POST", body: JSON.stringify({ email }) });
}

/**
 * Verify a magic-link token and return user identity + session token.
 * @param {string} token
 * @returns {Promise<{user_id: string, email: string, token: string}>}
 */
export async function verifyMagicLink(token) {
  return request(`/auth/verify?token=${encodeURIComponent(token)}`);
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

/**
 * Fetch the price time series for a search.
 * @param {string} searchId
 * @param {number|null} [days=30]  Number of days to look back. Pass null for all-time.
 * @returns {Promise<object[]>} PriceHistoryPointResponse[]
 */
export async function getPriceHistory(searchId, days = 30) {
  const qs = days != null ? `?days=${days}` : "?days=3650";
  return request(`/searches/${searchId}/price-history${qs}`);
}

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
 * @param {boolean} triggerPurchase
 * @returns {Promise<object>} AlertResponse
 */
export async function confirmAlert(alertId, triggerPurchase = false) {
  return request(`/alerts/${alertId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ trigger_purchase: triggerPurchase }),
  });
}
