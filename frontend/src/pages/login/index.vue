<template>
  <view class="login-page">
    <!-- 装饰圆 -->
    <view class="deco-circle deco-1" />
    <view class="deco-circle deco-2" />
    <view class="deco-circle deco-3" />

    <!-- 品牌区域 -->
    <view class="brand-area fade-in">
      <view class="logo-outer">
        <image class="logo-icon" src="/static/icons/logo-app.png" mode="aspectFit" />
      </view>
      <text class="brand-name">易挂念</text>
      <text class="brand-subtitle">家人牵挂平台</text>

      <view class="brand-divider" />

      <text class="brand-quote">"让关心自然流动，让牵挂被看见"</text>
      <text class="brand-desc">连接家庭与社区，守护每一位长者</text>
    </view>

      <!-- 登录操作 -->
    <view class="login-actions fade-in stagger-2">
      <!-- 身份选择 -->
      <view class="role-pick-area">
        <text class="role-pick__label">请选择您的身份</text>
        <view class="role-pick">
          <view
            class="role-pick__opt"
            :class="{ 'role-pick__opt--on': selectedRole === 'family' }"
            @tap="selectedRole = 'family'"
          >
            <text class="role-pick__text">子女/亲属</text>
          </view>
          <view
            class="role-pick__opt"
            :class="{ 'role-pick__opt--on': selectedRole === 'elder' }"
            @tap="selectedRole = 'elder'"
          >
            <text class="role-pick__text">长辈</text>
          </view>
        </view>
      </view>

      <button class="wx-login-btn" :class="{ 'wx-login-btn--dim': !canSubmit }" @tap="handleLogin()">
        <text class="wx-btn-text">微信一键登录</text>
      </button>

      <!-- 开发环境调试入口（生产构建自动隐藏） -->
      <view v-if="isDev" class="dev-login-group">
        <button class="dev-login-btn" @tap="handleLogin('demo_family')">
          <text class="dev-btn-text">子女端体验</text>
        </button>
        <button class="dev-login-btn" @tap="handleLogin('demo_elder')">
          <text class="dev-btn-text">长辈端体验</text>
        </button>
      </view>

      <view class="terms-row">
        <view class="terms-check" :class="{ 'terms-check--on': agreed }" @tap="agreed = !agreed">
          <text v-if="agreed" class="terms-check__tick">✓</text>
        </view>
        <view class="terms-text">
          <text class="terms-text__plain" @tap="agreed = !agreed">我已阅读并同意</text>
          <text class="terms-text__link" @tap.stop="goAgreement">《用户协议》</text>
          <text class="terms-text__plain" @tap="agreed = !agreed">与</text>
          <text class="terms-text__link" @tap.stop="goPrivacy">《隐私政策》</text>
        </view>
      </view>
    </view>

    <!-- Footer -->
    <text class="login-footer">DESIGNED FOR HUMAN CONNECTION</text>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const isDev = import.meta.env.DEV;
const agreed = ref(false);
const selectedRole = ref("");
const redirectUrl = ref("");
const canSubmit = computed(() => !!selectedRole.value && agreed.value);

onLoad((query) => {
  // 分享卡片直达等场景：登录成功后回跳到目标页
  if (query?.redirect) {
    try {
      redirectUrl.value = decodeURIComponent(query.redirect);
    } catch {
      redirectUrl.value = "";
    }
  }
});

function goAgreement() {
  uni.navigateTo({ url: "/pages/about/agreement" });
}

function goPrivacy() {
  uni.navigateTo({ url: "/pages/about/privacy" });
}

async function handleLogin(openid) {
  // 真实微信登录需先选身份 + 同意协议；调试入口（openid 直登）仅需协议
  if (!openid && !selectedRole.value) {
    uni.showToast({ title: "请先选择您的身份", icon: "none" });
    return;
  }
  if (!agreed.value) {
    uni.showToast({ title: "请先阅读并勾选同意相关协议", icon: "none" });
    return;
  }
  try {
    uni.showLoading({ title: "登录中..." });
    await userStore.login(openid);
    uni.hideLoading();

    // 按登录页所选身份初始化/校正（存量账号若与所选身份不同，同样生效）
    if (selectedRole.value && userStore.profile?.role !== selectedRole.value) {
      try {
        await userStore.setRole(selectedRole.value);
      } catch {
        // 设定失败时由下方 hasRole 分支兜底跳转角色页
      }
    }

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
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, $c-text 0%, $c-primary-hover 100%);
  padding: $sp-32 $sp-24;
  position: relative;
  overflow: hidden;
}

// ── 装饰圆 ──
.deco-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.04);
  pointer-events: none;
}

.deco-1 {
  width: 700rpx;
  height: 700rpx;
  top: -120rpx;
  left: -200rpx;
}

.deco-2 {
  width: 500rpx;
  height: 500rpx;
  top: 40%;
  left: 20%;
}

.deco-3 {
  width: 600rpx;
  height: 600rpx;
  bottom: -180rpx;
  right: -200rpx;
}

// ── 品牌区域 ──
.brand-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  position: relative;
  z-index: 1;
  margin-bottom: 80rpx;
}

.logo-outer {
  width: 160rpx;
  height: 160rpx;
  border-radius: 36rpx;
  overflow: hidden;
  margin-bottom: 40rpx;
  box-shadow: 0 10rpx 36rpx rgba(0, 0, 0, 0.28);
}

.logo-icon {
  width: 100%;
  height: 100%;
  display: block;
}

.brand-name {
  font-size: 96rpx;
  font-weight: $fw-bold;
  color: $c-text-inverse;
  letter-spacing: 4rpx;
  display: block;
  margin-bottom: $sp-6;
}

.brand-subtitle {
  font-size: 30rpx;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 12rpx;
  display: block;
  font-weight: $fw-medium;
}

.brand-divider {
  width: 200rpx;
  height: 1rpx;
  background: rgba(255, 255, 255, 0.12);
  margin: 48rpx 0;
}

.brand-quote {
  font-size: 32rpx;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 2rpx;
  display: block;
  line-height: $lh-relaxed;
  font-weight: $fw-medium;
}

.brand-desc {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 12rpx;
  letter-spacing: 2rpx;
  display: block;
}

// ── 登录操作 ──
.login-actions {
  width: 100%;
  max-width: 560rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24rpx;
  position: relative;
  z-index: 1;
}

.dev-login-group {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

// ── 身份选择 ──
.role-pick-area {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 8rpx;
}

.role-pick__label {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 2rpx;
}

.role-pick {
  width: 100%;
  display: flex;
  gap: 20rpx;
}

.role-pick__opt {
  flex: 1;
  height: 92rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $r-full;
  border: 2rpx solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.06);
  transition: all $duration-normal $ease-out;
  &:active {
    transform: scale(0.97);
  }
}

.role-pick__opt--on {
  background: #C4745C;
  border-color: #C4745C;
  box-shadow: 0 6rpx 24rpx rgba(196, 116, 92, 0.45);
}

.role-pick__text {
  font-size: 30rpx;
  font-weight: $fw-medium;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 2rpx;
}

.role-pick__opt--on .role-pick__text {
  color: #FFFFFF;
}

.wx-login-btn {
  width: 100%;
  height: 104rpx;
  background-color: #07C160; // WeChat brand green
  border-radius: $r-full;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  box-shadow: 0 8rpx 32rpx rgba(7, 193, 96, 0.30);
  transition: all $duration-normal $ease-out;
  &:active {
    transform: scale(0.95);
    opacity: 0.9;
  }
  &--dim {
    opacity: 0.4;
    box-shadow: none;
  }
  &::after { border: none; }
}

.wx-btn-text {
  font-size: $fs-subtitle;
  font-weight: $fw-semibold;
  color: $c-text-inverse;
  letter-spacing: 4rpx;
}

.dev-login-btn {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1rpx solid rgba(255, 255, 255, 0.15);
  border-radius: $r-full;
  padding: 20rpx 48rpx;
  transition: all $duration-normal $ease-out;
  &:active {
    background: rgba(255, 255, 255, 0.12);
    transform: scale(0.97);
  }
  &::after { border: none; }
}

.dev-btn-text {
  font-size: 28rpx;
  font-weight: $fw-medium;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 2rpx;
}

// ── 协议勾选 ──
.terms-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  margin-top: 24rpx;
  padding: 8rpx 12rpx;
}

.terms-check {
  width: 34rpx;
  height: 34rpx;
  border-radius: 50%;
  border: 2rpx solid rgba(255, 255, 255, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all $duration-fast $ease-out;

  &--on {
    background: #C4745C;
    border-color: #C4745C;
  }

  &__tick {
    font-size: 24rpx;
    color: #FFFFFF;
    line-height: 1;
  }
}

.terms-text {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;

  &__plain {
    font-size: 24rpx;
    color: rgba(255, 255, 255, 0.42);
  }

  &__link {
    font-size: 24rpx;
    color: #E8B7A6;
    font-weight: $fw-medium;
  }
}

// ── Footer ──
.login-footer {
  position: absolute;
  bottom: 48rpx;
  left: 48rpx;
  font-size: 18rpx;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 2rpx;
  font-weight: $fw-medium;
}
</style>
