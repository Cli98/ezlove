import { ref } from "vue";

// 登录令牌的响应式镜像：uni storage 不是响应式 API，
// 只在 computed 里读 storage 会导致登录成功后 isLoggedIn 不更新
export const authToken = ref(uni.getStorageSync("access_token") || "");

export function setAuthToken(token) {
  if (token) uni.setStorageSync("access_token", token);
  else uni.removeStorageSync("access_token");
  authToken.value = token || "";
}

// 启动或跨模块改动存储后，把内存状态与存储对齐
export function syncAuthToken() {
  authToken.value = uni.getStorageSync("access_token") || "";
}