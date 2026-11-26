/**
 * LIFE TODAY — AI NEWSROOM V1.0
 * API Client SDK
 */

const API_BASE = ""; // Relative path to FastAPI backend

async function apiRequest(endpoint, options = {}) {
  try {
    const savedPin = localStorage.getItem("newsroom_pin") || "";
    const headers = {
      "Content-Type": "application/json",
      ...(savedPin ? { "X-Newsroom-Pin": savedPin } : {}),
      ...options.headers,
    };
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });
    if (res.status === 401 && endpoint !== "/api/auth/verify") {
      const overlay = document.getElementById("pin-lock-overlay");
      if (overlay) overlay.style.display = "flex";
      throw new Error("Cần nhập mã PIN truy cập.");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Request failed with status ${res.status}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    throw error;
  }
}

export const API = {
  // Settings & System Status
  getSystemStatus: () => apiRequest("/api/settings/status"),
  getStorageStats: () => apiRequest("/api/settings/storage"),
  cleanupStorage: (maxAgeHours = 24) => apiRequest(`/api/settings/cleanup?max_age_hours=${maxAgeHours}`, { method: "POST" }),
  updateSettings: (data) => apiRequest("/api/settings", { method: "POST", body: JSON.stringify(data) }),
  toggleEmergencyStop: () => apiRequest("/api/settings/emergency_stop", { method: "POST" }),

  // News Hunter
  scanNews: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/api/news/scan?${q}`, { method: "POST" });
  },
  listArticles: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/api/news?${q}`);
  },
  getArticle: (id) => apiRequest(`/api/news/${id}`),
  processArticle: (id) => apiRequest(`/api/news/${id}/process`, { method: "POST" }),
  rejectArticle: (id, reason) => apiRequest(`/api/news/${id}/reject?reason=${encodeURIComponent(reason || '')}`, { method: "POST" }),

  // Posts & Publishing
  listPosts: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/api/posts?${q}`);
  },
  getPost: (id) => apiRequest(`/api/posts/${id}`),
  updatePost: (id, data) => apiRequest(`/api/posts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  regeneratePostCaption: (id) => apiRequest(`/api/posts/${id}/regenerate-caption`, { method: "POST" }),
  approvePost: (id) => apiRequest(`/api/posts/${id}/approve`, { method: "POST" }),
  publishPostNow: (id) => apiRequest(`/api/posts/${id}/publish`, { method: "POST" }),
  schedulePost: (id, customTime) => apiRequest(`/api/posts/${id}/schedule${customTime ? `?custom_time=${encodeURIComponent(customTime)}` : ''}`, { method: "POST" }),
  cancelPost: (id) => apiRequest(`/api/posts/${id}/cancel`, { method: "POST" }),
  deletePost: (id) => apiRequest(`/api/posts/${id}`, { method: "DELETE" }),

  // Media & Rights
  listMedia: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/api/media?${q}`);
  },
  updateMediaRights: (uuid, data) => apiRequest(`/api/media/${uuid}/rights`, { method: "PUT", body: JSON.stringify(data) }),

  // Sources
  listSources: () => apiRequest("/api/sources"),
  checkSourceHealth: (id) => apiRequest(`/api/sources/${id}/check`, { method: "POST" }),
  updateSource: (id, data) => apiRequest(`/api/sources/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  // Facebook
  getFacebookStatus: () => apiRequest("/api/facebook/status"),

  // Analytics
  getContentMix: () => apiRequest("/api/analytics/mix"),
  getAuditLogs: (limit = 100) => apiRequest(`/api/analytics/logs?limit=${limit}`),
};
