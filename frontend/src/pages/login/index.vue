<template>
  <view class="login-page">
    <view class="brand-area">
      <image class="brand-art" src="/static/brand/login-hero-v5.jpg" mode="widthFix" />
    </view>

    <view class="login-actions">
      <view class="login-heading">
        <text class="login-heading__title">欢迎回来</text>
        <text class="login-heading__sub">用一点关心，拉近心的距离</text>
      </view>

      <button class="wx-login-btn" @tap="handleLogin()">
        <u-icon name="weixin-fill" color="#FFFFFF" size="25" />
        <text class="wx-btn-text">微信一键登录</text>
      </button>

      <view v-if="isDev" class="dev-divider">
        <view class="dev-divider__line"></view>
        <text class="dev-divider__text">其他方式体验</text>
        <view class="dev-divider__line"></view>
      </view>

      <view v-if="isDev" class="dev-login-group">
        <button class="dev-login-btn" @tap="handleLogin('demo_family')">
          <image class="dev-icon" src="/static/icons/login-family.svg" mode="aspectFit" />
          <text class="dev-btn-text">子女端</text>
          <text class="dev-btn-desc">关心家人</text>
        </button>
        <button class="dev-login-btn" @tap="handleLogin('demo_elder')">
          <image class="dev-icon" src="/static/icons/login-elder.svg" mode="aspectFit" />
          <text class="dev-btn-text">长辈端</text>
          <text class="dev-btn-desc">大字更友好</text>
        </button>
      </view>

      <view class="agreement-row" @tap="agreementAccepted = !agreementAccepted">
        <view class="agreement-check" :class="{ 'agreement-check--active': agreementAccepted }">
          <text v-if="agreementAccepted">✓</text>
        </view>
        <view class="agreement-copy">
          <text>我已阅读并同意</text>
          <text class="agreement-link" @tap.stop="goAgreement">《用户协议》</text>
          <text>与</text>
          <text class="agreement-link" @tap.stop="goPrivacy">《隐私政策》</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const isDev = import.meta.env.DEV;
const agreementAccepted = ref(false);
const redirectUrl = ref("");

onLoad((query) => {
  if (!query?.redirect) return;
  try {
    redirectUrl.value = decodeURIComponent(query.redirect);
  } catch {
    redirectUrl.value = "";
  }
});

function goAgreement() {
  uni.navigateTo({ url: "/pages/about/agreement" });
}

function goPrivacy() {
  uni.navigateTo({ url: "/pages/about/privacy" });
}

async function handleLogin(openid) {
  if (!agreementAccepted.value) {
    uni.showToast({ title: "请先阅读并同意服务协议与隐私政策", icon: "none" });
    return;
  }
  try {
    uni.showLoading({ title: "登录中..." });
    await userStore.login(openid);
    if (openid === "demo_family" || openid === "demo_elder") {
      await userStore.setRole(openid === "demo_family" ? "family" : "elder");
    }
    uni.hideLoading();

    if (redirectUrl.value) {
      uni.reLaunch({ url: redirectUrl.value });
    } else if (!userStore.hasRole) {
      uni.reLaunch({ url: "/pages/login/role" });
    } else {
      uni.reLaunch({ url: "/pages/index/index" });
    }
  } catch (e) {
    uni.hideLoading();
    uni.showToast({ title: "登录失败，请重试", icon: "none" });
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow-x: hidden;
  box-sizing: border-box;
  background: $c-bg;
}

.brand-area {
  width: 100%;
  height: 57vh;
  flex: none;
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
}

.brand-art {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: auto;
  display: block;
}

.login-actions {
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18rpx;
  position: relative;
  z-index: 2;
  margin-top: -42rpx;
  padding: 42rpx 46rpx calc(18rpx + env(safe-area-inset-bottom));
  border-radius: 48rpx 48rpx 0 0;
  box-sizing: border-box;
  background: rgba(255, 252, 248, 0.99);
}

.login-heading {
  width: 100%;
  margin-bottom: 10rpx;
  text-align: center;

  &__title {
    display: block;
    color: $c-text;
    font-family: "Songti SC", "STSong", "SimSun", serif;
    font-size: 62rpx;
    font-weight: 900;
  }

  &__sub {
    display: block;
    margin-top: 8rpx;
    color: $c-text-sub;
    font-size: 27rpx;
  }
}

.wx-login-btn {
  width: 100%;
  height: 112rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  border: 0;
  border-radius: 48rpx;
  background: linear-gradient(100deg, #C44D3E 0%, #E47A5F 100%);
  box-shadow: 0 8rpx 24rpx rgba($c-primary, 0.22);

  &:active { transform: scale(0.98); opacity: 0.92; }
  &::after { border: 0; }
}

.wx-btn-text {
  color: #FFFFFF;
  font-size: 32rpx;
  font-weight: 600;
  letter-spacing: 3rpx;
}

.dev-divider {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 12rpx;

  &__line { flex: 1; height: 1rpx; background: $c-border; }
  &__text { color: $c-text-hint; font-size: 24rpx; }
}

.dev-login-group {
  width: 100%;
  align-self: center;
  display: flex;
  gap: 24rpx;
  margin-top: 4rpx;
}

.dev-login-btn {
  min-width: 0;
  height: 184rpx;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0 4rpx;
  border: 0;
  border-radius: 24rpx;
  background: #F7F1EA;

  &:active { transform: scale(0.97); background: $c-primary-bg; }
  &::after { border: 0; }
}

.dev-btn-text {
  margin-top: 10rpx;
  color: $c-text;
  font-size: 28rpx;
  font-weight: 600;
  line-height: 1.2;
  white-space: nowrap;
}

.dev-btn-desc {
  margin-top: 6rpx;
  color: $c-text-hint;
  font-size: 20rpx;
  line-height: 1.2;
  white-space: nowrap;
}

.dev-icon {
  width: 64rpx;
  height: 64rpx;
  flex: none;
}

.agreement-row {
  width: 100%;
  min-height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  color: $c-text-hint;
  font-size: 22rpx;
}

.agreement-check {
  width: 32rpx;
  height: 32rpx;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid $c-border;
  border-radius: 50%;
  box-sizing: border-box;
  color: #FFFFFF;
  font-size: 22rpx;

  &--active {
    border-color: $c-primary;
    background: $c-primary;
  }
}

.agreement-copy {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.agreement-link {
  color: $c-primary;
}
</style>
