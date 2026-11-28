import { api, tokens, unwrap } from "./client";

export async function fetchMe() {
  return unwrap(await api.get("/auth/me/"));
}

export async function login(username, password) {
  const res = await api.post("/auth/login/", { username, password });
  tokens.save(unwrap(res));
  return fetchMe();
}

export async function logout() {
  try {
    if (tokens.refresh) await api.post("/auth/logout/", { refresh: tokens.refresh });
  } catch {
    /* the token may already be invalid, we still sign out locally */
  }
  tokens.clear();
}