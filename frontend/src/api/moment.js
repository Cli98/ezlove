import { api } from "./request";

export function sendMoment(data) {
  return api.post("/moments", data);
}

export function getMoments(params) {
  return api.get("/moments", params);
}

export function getMomentDetail(id) {
  return api.get(`/moments/${id}`);
}

export function deleteMoment(id) {
  return api.delete(`/moments/${id}`);
}

export function recordView(id) {
  return api.post(`/moments/${id}/view`);
}

export function sendResponse(id, data) {
  return api.post(`/moments/${id}/response`, data);
}
