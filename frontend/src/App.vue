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

  // 未登录时不强制跳登录页：先让用户体验首页与功能介绍，
  // 需要身份的功能由页面在用户主动点击时引导登录（应用审核要求先体验后授权）
}

// 分享卡片直达页：允许未完成角色选择的用户直接停留（页面内自行请求与引导）
function isShareTarget(path) {
  return path === "pages/view/detail";
}
</script>

<style lang="scss">
@import "@/styles/base.scss";
</style>
