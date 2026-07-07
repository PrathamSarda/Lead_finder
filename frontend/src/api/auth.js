import apiClient from "./client";

export const authApi = {
  login: (payload) => apiClient.post("/auth/login", payload).then((res) => res.data),
  register: (payload) => apiClient.post("/auth/register", payload).then((res) => res.data),
  refresh: (refreshToken) =>
    apiClient.post("/auth/refresh", { refresh_token: refreshToken }).then((res) => res.data),
  me: () => apiClient.get("/users/me").then((res) => res.data),
};
