import { api } from "./request";

/** 查询各 AI 功能的积分消耗 */
export function getAiMediaCost() {
  return api.get("/ai/media/cost");
}

/** AI 照片生成视频 */
export function generateVideo(imageUrl, style = "default") {
  return api.post("/ai/media/generate-video", { image_url: imageUrl, style });
}

/** AI 老照片修复 */
export function restorePhoto(imageUrl, enhanceColor = true) {
  return api.post("/ai/media/restore-photo", { image_url: imageUrl, enhance_color: enhanceColor });
}

/** AI 照片动画化（新照片转视频） */
export function animatePhoto(imageUrl, durationSeconds = 5) {
  return api.post("/ai/media/animate-photo", {
    image_url: imageUrl,
    duration_seconds: durationSeconds,
  });
}
