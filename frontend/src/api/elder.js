import { api } from "./request";

export function getElderStatus(elderId) {
  return api.get(`/elders/${elderId}/status`);
}

export function getElderActivity(elderId, params) {
  return api.get(`/elders/${elderId}/activity`, params);
}

export function manualCheckin(elderId) {
  return api.post(`/elders/${elderId}/checkin`);
}
