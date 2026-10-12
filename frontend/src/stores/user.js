import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { wxLogin, devLogin } from "@/api/auth";
import { getMe, updateMe } from "@/api/user";

export const useUserStore = defineStore("user", () => {
  const profile = ref(null);
  const isLoggedIn = computed(() => !!uni.getStorageSync("access_token"));
  const hasRole = computed(() => !!profile.value?.role);
  const isFamily = computed(() => profile.value?.role === "family");
  const isElder = computed(() => profile.value?.role === "elder");

  // 分享卡片直达页需要等待启动时的静默登录完成后再请求内容
  let loginReadyPromise = null;

  function markLoginReady(promise) {
    loginReadyPromise = promise;
  }

  async function waitLoginReady() {
    if (!loginReadyPromise) return;
    try {
      await loginReadyPromise;
    } catch {
      // 启动异常由页面自己的错误态兜底
    }
  }

  async function checkLogin() {
    const token = uni.getStorageSync("access_token");
    if (!token) return;
    try {
      profile.value = await getMe();
    } catch {
      uni.removeStorageSync("access_token");
      profile.value = null;
    }
  }

  async function login(openid) {
    if (openid) {
      const res = await devLogin(openid);
      uni.setStorageSync("access_token", res.access_token);
      uni.setStorageSync("refresh_token", res.refresh_token);
      profile.value = res.user;
      return;
    }

    // #ifdef MP-WEIXIN
    const { code } = await new Promise((resolve, reject) => {
      uni.login({ success: resolve, fail: reject });
    });
    const res = await wxLogin(code);
    // #endif
    // #ifdef H5
    const res = await devLogin();
    // #endif
    uni.setStorageSync("access_token", res.access_token);
    uni.setStorageSync("refresh_token", res.refresh_token);
    profile.value = res.user;
  }

  async function setRole(role) {
    return updateProfile({ role });
  }

  async function updateProfile(data) {
    profile.value = await updateMe(data);
    return profile.value;
  }

  function logout() {
    uni.removeStorageSync("access_token");
    uni.removeStorageSync("refresh_token");
    profile.value = null;
    uni.reLaunch({ url: "/pages/login/index" });
  }

  return {
    profile,
    isLoggedIn,
    hasRole,
    isFamily,
    isElder,
    checkLogin,
    login,
    setRole,
    updateProfile,
    logout,
    markLoginReady,
    waitLoginReady,
  };
});
