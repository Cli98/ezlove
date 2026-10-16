import { api } from "./request";

export function getContributors() {
  return api.get("/contributors");
}
