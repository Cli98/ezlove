<template>
  <view class="role-page">
    <image class="page-botanical" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/role/role-botanical.png" mode="aspectFit" />

    <view class="role-content">
      <view class="role-nav" :style="navMetrics.barStyle">
        <view class="role-nav__back" @tap="goBack">
          <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
        </view>
      </view>

      <view class="hero-section fade-in">
        <text class="hero-title">你是</text>
        <text class="hero-subtitle">选择一个身份，开启温暖的陪伴</text>
      </view>

      <view class="role-cards">
        <view
          class="role-card fade-in stagger-1"
          :class="{ 'role-card--active': selectedRole === 'family' }"
          @tap="selectedRole = 'family'"
        >
          <image class="role-card-art" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/role/family-role-art.png" mode="aspectFit" />
          <view class="role-card-copy">
            <text class="role-card-title">子女/亲属</text>
            <text class="role-card-desc">每天发送牵挂，</text>
            <text class="role-card-desc">让老人知道你惦记Ta</text>
          </view>
          <view class="role-check" :class="{ 'role-check--active': selectedRole === 'family' }">
            <text v-if="selectedRole === 'family'">✓</text>
          </view>
        </view>

        <view
          class="role-card fade-in stagger-2"
          :class="{ 'role-card--active': selectedRole === 'elder' }"
          @tap="selectedRole = 'elder'"
        >
          <image class="role-card-art role-card-art--elder" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/role/elder-role-art.png" mode="aspectFit" />
          <view class="role-card-copy">
            <text class="role-card-title">长辈</text>
            <text class="role-card-desc">查看孩子们的问候，</text>
            <text class="role-card-desc">用表情回应关爱</text>
          </view>
          <view class="role-check" :class="{ 'role-check--active': selectedRole === 'elder' }">
            <text v-if="selectedRole === 'elder'">✓</text>
          </view>
        </view>
      </view>

      <view class="role-note">
        <view class="role-note__line" />
        <text>选择后可随时切换</text>
        <view class="role-note__line" />
      </view>

      <button class="confirm-btn" @tap="confirmRole">
        <text class="confirm-btn-text">开启挂念之旅</text>
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { useUserStore } from "@/stores/user";
import { getNavigationBarMetrics } from "@/utils/navigation";

const userStore = useUserStore();
const navMetrics = getNavigationBarMetrics();
const selectedRole = ref(userStore.profile?.role || "family");

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack();
    return;
  }
  uni.reLaunch({ url: "/pages/login/index" });
}

async function confirmRole() {
  try {
    uni.showLoading({ title: "保存中...", mask: true });
    if (selectedRole.value !== userStore.profile?.role) {
      await userStore.setRole(selectedRole.value);
    }
    uni.hideLoading();
    uni.reLaunch({ url: "/pages/index/index" });
  } catch {
    uni.hideLoading();
    uni.showToast({ title: "设置失败，请重试", icon: "none" });
  }
}
</script>

<style lang="scss" scoped>
.role-page {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at 12% 8%, rgba($c-accent, 0.08), transparent 24%), $c-bg;
}

.page-botanical {
  position: absolute;
  z-index: 0;
  right: -58rpx;
  bottom: 176rpx;
  width: 430rpx;
  height: 640rpx;
  opacity: 0.34;
  pointer-events: none;
}

.role-content {
  min-height: 100vh;
  position: relative;
  z-index: 1;
  padding: 0 40rpx calc(36rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.role-nav {
  box-sizing: content-box;
  display: flex;
  align-items: center;
  position: relative;

  &__back {
    width: 72rpx;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-left: -20rpx;
  }

  image { width: 34rpx; height: 34rpx; }
}
.hero-section { margin: 46rpx 0 42rpx; text-align: center; }
.hero-title { display: block; color: $c-text; font-family: "Songti SC", "STSong", serif; font-size: 68rpx; font-weight: 900; line-height: 1.15; }
.hero-subtitle { display: block; margin-top: 14rpx; color: $c-text-sub; font-size: 28rpx; }
.role-cards { display: flex; flex-direction: column; gap: 24rpx; }

.role-card {
  height: 286rpx;
  position: relative;
  overflow: hidden;
  border: 2rpx solid rgba($c-border, 0.88);
  border-radius: 30rpx;
  background: rgba(255, 252, 249, 0.9);
  box-shadow: $shadow-sm;
  transition: transform $duration-fast $ease-out, border-color $duration-fast $ease-out;
  &:active { transform: scale(0.985); }
}

.role-card--active {
  border: 4rpx solid $c-primary;
  background: linear-gradient(135deg, rgba(255, 250, 247, 0.98), rgba(251, 239, 234, 0.98));
  box-shadow: 0 10rpx 30rpx rgba($c-primary, 0.12);
}

.role-card-art { position: absolute; left: -20rpx; bottom: -10rpx; width: 390rpx; height: 300rpx; }
.role-card-art--elder { left: -30rpx; }
.role-card-copy { position: absolute; z-index: 2; left: 276rpx; right: 66rpx; top: 50%; transform: translateY(-50%); }
.role-card-title { display: block; margin-bottom: 20rpx; color: $c-text; font-family: "Songti SC", "STSong", serif; font-size: 40rpx; font-weight: 800; line-height: 1.2; }
.role-card-desc { display: block; color: $c-text-sub; font-size: 25rpx; line-height: 1.5; white-space: nowrap; }

.role-check {
  width: 44rpx;
  height: 44rpx;
  position: absolute;
  z-index: 3;
  right: 24rpx;
  top: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translateY(-50%);
  border: 3rpx solid #A69D95;
  border-radius: 50%;
  color: $c-text-inverse;
  font-size: 28rpx;
  font-weight: $fw-bold;
  &--active { border-color: $c-primary; background: $c-primary; }
}

.role-note {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin: 56rpx 26rpx 40rpx;
  color: $c-text-hint;
  font-size: 23rpx;
  text-align: center;
  &__line { height: 1rpx; flex: 1; background: $c-border; }
}

.confirm-btn {
  width: 100%;
  height: 106rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: $r-full;
  background: $gradient-warm;
  box-shadow: $shadow-glow;
  transition: transform $duration-fast $ease-out;
  &:active { transform: scale(0.98); }
  &::after { border: none; }
}

.confirm-btn-text { color: $c-text-inverse; font-family: "Songti SC", "STSong", serif; font-size: 36rpx; font-weight: $fw-bold; letter-spacing: 2rpx; }
</style>
