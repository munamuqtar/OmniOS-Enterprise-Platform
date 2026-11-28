import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const ACCESS = "omnios_access";
const REFRESH = "omnios_refresh";

export const tokens = {
  get access() { return localStorage.getItem(ACCESS); },
  get refresh() { return localStorage.getItem(REFRESH); },
  save({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

export const api = axios.create({ baseURL: BASE_URL, headers: { "Content-Type": "application/json" } });

/** Success bodies are {success, message, data, errors}; plain bodies pass through unchanged. */
export const unwrap = (res) => {
  const body = res.data;
  return body && typeof body === "object" && "success" in body && "data" in body ? body.data : body;
};

api.interceptors.request.use((config) => {
  if (tokens.access) config.headers.Authorization = `Bearer ${tokens.access}`;
  return config;
});

let onAuthLost = () => {};
export const setAuthLostHandler = (fn) => { onAuthLost = fn; };

let refreshing = null;   // one refresh at a time, even if many requests fail together
function refreshAccess() {
  if (!tokens.refresh) return Promise.reject(new Error("No refresh token"));
  if (!refreshing) {
    refreshing = axios
      .post(`${BASE_URL}/auth/refresh/`, { refresh: tokens.refresh })
      .then((res) => { tokens.save(unwrap(res)); return tokens.access; })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { response, config } = error;
    const isAuthCall = /\/auth\/(login|refresh)\//.test(config?.url || "");
    if (response?.status === 401 && config && !config._retried && !isAuthCall) {
      config._retried = true;
      try {
        await refreshAccess();
        return api(config);              // replay the original request with the new token
      } catch {
        tokens.clear();
        onAuthLost();
      }
    }
    return Promise.reject(error);
  }
);