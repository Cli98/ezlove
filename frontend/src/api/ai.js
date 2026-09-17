import { api } from "./request";

export function getAiSuggestions(elderId) {
  return api.post("/ai/suggest", { elder_id: elderId });
}
