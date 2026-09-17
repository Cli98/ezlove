<script setup>
import { onLaunch } from "@dcloudio/uni-app";
import { useUserStore } from "./stores/user";

onLaunch(async () => {
  const userStore = useUserStore();
  await userStore.checkLogin();

  if (!userStore.isLoggedIn) {
    // #ifdef MP-WEIXIN
    uni.reLaunch({ url: "/pages/login/index" });
    // #endif
    // #ifdef H5
    uni.reLaunch({ url: "/pages/login/index" });
    // #endif
    return;
  }

  if (!userStore.hasRole) {
    uni.reLaunch({ url: "/pages/login/role" });
    return;
  }
});
</script>

<style lang="scss">
@import "@/styles/base.scss";
</style>
