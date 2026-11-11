// 小程序功能开关
// 关闭后仅隐藏入口，页面与相关代码保留，需要恢复时改回 true 即可
// 注意：恢复 AI 功能时还需把 pages/send/ai-suggest、pages/send/ai-media 重新登记到 pages.json
export const FEATURES = {
  aiChat: false, // AI 帮我写：生成式文案建议
  aiCreation: false, // AI 创作：生成式图片/视频内容
  // 入口文案默认保持中性，避免审核关键词命中；恢复功能时可自行调整
  aiChatLabel: "帮我写",
  aiCreationLabel: "帮我创作",
};