import { api } from "./request";

export function registerVolunteer() {
  return api.post("/volunteer/register");
}

export function getMyProfile() {
  return api.get("/volunteer/my-profile");
}

export function getAvailableTasks() {
  return api.get("/volunteer/available-tasks");
}

export function acceptTask(taskId) {
  return api.post(`/volunteer/tasks/${taskId}/accept`);
}

export function completeTask(taskId, data) {
  return api.post(`/volunteer/tasks/${taskId}/complete`, data);
}

export function getMyPoints() {
  return api.get("/volunteer/my-points");
}
