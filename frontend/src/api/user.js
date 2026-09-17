import { api } from "./request";

export function getMe() {
  return api.get("/users/me");
}

export function updateMe(data) {
  return api.put("/users/me", data);
}

export function selfCheckIn() {
  return api.post("/users/check-in");
}

export function getTodayCheckIn() {
  return api.get("/users/check-in/today");
}
