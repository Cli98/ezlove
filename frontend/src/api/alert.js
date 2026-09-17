import { api } from "./request";

export function getAlerts(params) {
  return api.get("/alerts", params);
}

export function resolveAlert(id) {
  return api.put(`/alerts/${id}/resolve`);
}
