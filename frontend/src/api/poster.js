import { api } from "./request";

export function generatePoster(data) {
  return api.post("/poster/generate", data);
}

export function renderSinglePoster(data) {
  return api.post("/poster/render-single", data);
}
