<script setup>
import { onLaunch } from "@dcloudio/uni-app";
import { useUserStore } from "./stores/user";

onLaunch(async () => {
  const userStore = useUserStore();
  const boot = bootstrap(userStore);
  userStore.markLoginReady(boot);
  await boot;
});

async function bootstrap(userStore) {
  // 记录启动入口，未登录时用于登录后回跳（分享卡片直达场景）
  const launch = uni.getLaunchOptionsSync ? uni.getLaunchOptionsSync() : {};
  const entryPath = launch.path || "";
  const entryUrl = buildEntryUrl(entryPath, launch.query);

  await userStore.checkLogin();

  if (userStore.isLoggedIn) {
    if (!userStore.hasRole && !isShareTarget(entryPath)) {
      uni.reLaunch({ url: "/pages/login/role" });
    }
    return;
  }

  // 开发环境允许直接预览身份选择页，避免启动守卫立即跳回登录页
  if (import.meta.env.DEV && entryPath === "pages/login/role") {
    return;
  }

  // 分享卡片直达页：微信端先静默登录，让长辈无需操作即可查看
  // #ifdef MP-WEIXIN
  if (isShareTarget(entryPath)) {
    try {
      await userStore.login();
      return;
    } catch {
      // 静默登录失败，落登录页兜底
    }
  }
  // #endif

  const loginUrl = entryUrl
    ? `/pages/login/index?redirect=${encodeURIComponent(entryUrl)}`
    : "/pages/login/index";
  uni.reLaunch({ url: loginUrl });
}

// 分享卡片直达页：允许未完成角色选择的用户直接停留（页面内自行请求与引导）
function isShareTarget(path) {
  return path === "pages/view/detail";
}

function buildEntryUrl(path, query) {
  if (!path) return "";
  const qs = Object.keys(query || {})
    .map((k) => `${k}=${encodeURIComponent(query[k])}`)
    .join("&");
  return `/${path}${qs ? `?${qs}` : ""}`;
}
</script>

<style lang="scss">
@import "@/styles/base.scss";
</style>
