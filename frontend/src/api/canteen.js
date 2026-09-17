import { api } from "./request";

export function getTodayMenu() {
  return api.get("/community/canteen/menu/today");
}
