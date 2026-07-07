import apiClient from "./client";

export const companiesApi = {
  list: (params) => apiClient.get("/companies", { params }).then((res) => res.data),
  get: (id) => apiClient.get(`/companies/${id}`).then((res) => res.data),
  create: (payload) => apiClient.post("/companies", payload).then((res) => res.data),
  update: (id, payload) => apiClient.patch(`/companies/${id}`, payload).then((res) => res.data),
};
