import { api } from "./request";

export function createInvite() {
  return api.post("/relations/invite");
}

export function bindByCode(invite_code) {
  return api.post("/relations/bind", { invite_code });
}

export function getRelations() {
  return api.get("/relations");
}

export function updateRelation(id, data) {
  return api.put(`/relations/${id}`, data);
}

export function deleteRelation(id) {
  return api.delete(`/relations/${id}`);
}
