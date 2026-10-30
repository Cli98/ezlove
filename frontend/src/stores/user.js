import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { wxLogin, devLogin } from "@/api/auth";
import { getMe, updateMe } from "@/api/user";
import { authToken, setAuthToken, syncAuthToken } from "@/utils/auth-state";

export const useUserStore = defineStore("user", () => {
  const profile = ref(uni.getStorageSync("user_profile") || null);
  const isLoggedIn = computed(() => !!authToken.value);
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
    syncAuthToken();
    const token = uni.getStorageSync("access_token");
    if (!token) {
      setProfile(null);
      return;
    }
    try {
      setProfile(await getMe());
    } catch {
      // 认证失效由请求层清理；网络抖动时保留本地登录信息
      if (!uni.getStorageSync("access_token")) setProfile(null);
    }
  }

  function setProfile(value) {
    profile.value = value;
    if (value) uni.setStorageSync("user_profile", value);
    else uni.removeStorageSync("user_profile");
  }

  async function login(openid) {
    if (openid) {
      const res = await devLogin(openid);
      setAuthToken(res.access_token);
      uni.setStorageSync("refresh_token", res.refresh_token);
      setProfile(res.user);
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
    uni.setStorageSync("refresh_token", res.refresh_token);
    setAuthToken(res.access_token);
    setProfile(res.user);
  }

  async function setRole(role) {
    return updateProfile({ role });
  }

  async function updateProfile(data) {
    setProfile(await updateMe(data));
    return profile.value;
  }

  function logout() {
    setAuthToken("");
    uni.removeStorageSync("refresh_token");
    setProfile(null);
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
