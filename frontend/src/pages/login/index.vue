<template>
  <view class="login-page">
    <!-- 装饰圆 -->
    <view class="deco-circle deco-1" />
    <view class="deco-circle deco-2" />
    <view class="deco-circle deco-3" />

    <!-- 品牌区域 -->
    <view class="brand-area fade-in">
      <view class="logo-outer">
        <view class="logo-inner">
          <image class="logo-icon" src="/static/icons/logo-heart.svg" mode="aspectFit" />
        </view>
      </view>
      <text class="brand-name">易挂念</text>
      <text class="brand-subtitle">家人牵挂平台</text>

      <view class="brand-divider" />

      <text class="brand-quote">"让关心自然流动，让牵挂被看见"</text>
      <text class="brand-desc">连接家庭与社区，守护每一位长者</text>
    </view>

      <!-- 登录操作 -->
    <view class="login-actions fade-in stagger-2">
      <button class="wx-login-btn" @tap="handleLogin()">
        <text class="wx-btn-text">微信一键登录</text>
      </button>

      <!-- 开发环境调试入口 -->
      <view class="dev-login-group">
        <button class="dev-login-btn" @tap="handleLogin('demo_family')">
          <text class="dev-btn-text">子女端体验</text>
        </button>
        <button class="dev-login-btn" @tap="handleLogin('demo_elder')">
          <text class="dev-btn-text">长辈端体验</text>
        </button>
      </view>

      <text class="login-terms">登录即代表您已同意《服务协议》与《隐私政策》</text>
    </view>

    <!-- Footer -->
    <text class="login-footer">DESIGNED FOR HUMAN CONNECTION</text>
  </view>
</template>

<script setup>
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const isDev = import.meta.env.DEV;

async function handleLogin(openid) {
  try {
    uni.showLoading({ title: "登录中..." });
    await userStore.login(openid);
    uni.hideLoading();

    if (!userStore.hasRole) {
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
  border-radius: 32rpx;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8rpx;
  margin-bottom: 40rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.1);
}

.logo-inner {
  width: 100%;
  height: 100%;
  border-radius: 26rpx;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon {
  width: 64rpx;
  height: 64rpx;
  opacity: 0.9;
  filter: brightness(10);
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

.login-terms {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  margin-top: 24rpx;
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
