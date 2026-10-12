<template>
  <view class="role-page">
    <!-- 氛围背景 -->
    <view class="ambient-bg">
      <view class="ambient-circle ambient-1" />
      <view class="ambient-circle ambient-2" />
    </view>

    <!-- 返回（仅切换模式） -->
    <view
      v-if="mode === 'switch'"
      class="back-btn"
      :style="{ top: statusBarTop + 'px' }"
      @tap="goBack"
    >
      <image class="back-icon" src="/static/icons/arrow-back.svg" mode="aspectFit" />
    </view>

    <!-- 主内容 -->
    <view class="role-content">
      <!-- Hero -->
      <view class="hero-section fade-in">
        <text class="hero-title">{{ mode === 'switch' ? '切换身份' : '你是' }}</text>
      </view>

      <!-- 角色卡片 -->
      <view class="role-cards">
        <view
          class="role-card fade-in stagger-1"
          :class="{ 'role-card-active': selectedRole === 'family' }"
          @tap="selectedRole = 'family'"
        >
          <image class="role-card-icon" src="/static/icons/family.svg" mode="aspectFit" />
          <text class="role-card-title">子女/亲属</text>
          <text class="role-card-desc">每天发送牵挂，让老人知道你惦记Ta</text>
        </view>

        <view
          class="role-card fade-in stagger-2"
          :class="{ 'role-card-active': selectedRole === 'elder' }"
          @tap="selectedRole = 'elder'"
        >
          <image class="role-card-icon" src="/static/icons/elderly.svg" mode="aspectFit" />
          <text class="role-card-title">长辈</text>
          <text class="role-card-desc">查看孩子们的问候，用表情回应关爱</text>
        </view>
      </view>

      <!-- 确认按钮 -->
      <view class="confirm-area" :class="{ visible: selectedRole }">
        <button class="confirm-btn" @tap="confirmRole">
          <text class="confirm-btn-text">{{ mode === 'switch' ? '确认切换' : '开启挂念之旅' }}</text>
        </button>
      </view>
    </view>

    <!-- Footer -->
    <view class="role-footer fade-in stagger-3">
      <text class="footer-text">{{ mode === 'switch' ? '切换后立即生效' : '选择后可随时切换' }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const selectedRole = ref("");
const mode = ref("");
const statusBarTop = (uni.getSystemInfoSync().statusBarHeight || 20) + 8;

onLoad((query) => {
  mode.value = query?.mode || "";
  // 切换模式：预选当前身份
  if (mode.value === "switch" && userStore.profile?.role) {
    selectedRole.value = userStore.profile.role;
  }
});

function goBack() {
  uni.navigateBack();
}

async function confirmRole() {
  if (!selectedRole.value) return;
  try {
    await userStore.setRole(selectedRole.value);
    uni.reLaunch({ url: "/pages/index/index" });
  } catch (e) {
    uni.showToast({ title: "设置失败", icon: "none" });
  }
}
</script>

<style lang="scss" scoped>
.role-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: $c-bg;
  position: relative;
  overflow: hidden;
}

// ── 返回按钮（切换模式） ──
.back-btn {
  position: fixed;
  left: 32rpx;
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.04);
  z-index: 10;
  &:active {
    opacity: 0.7;
  }
}

.back-icon {
  width: 36rpx;
  height: 36rpx;
}

// ── 氛围背景 ──
.ambient-bg {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.ambient-circle {
  position: absolute;
  border-radius: 50%;
}

.ambient-1 {
  width: 40%;
  height: 40%;
  top: -10%;
  left: -10%;
  background: rgba($c-primary, 0.05);
  filter: blur(120rpx);
}

.ambient-2 {
  width: 30%;
  height: 30%;
  bottom: -5%;
  right: -5%;
  background: rgba($c-safe, 0.05);
  filter: blur(100rpx);
}

// ── 内容 ──
.role-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 160rpx $sp-24 0;
  position: relative;
  z-index: 1;
  max-width: 600rpx;
  margin: 0 auto;
  width: 100%;
}

.hero-section {
  text-align: center;
  margin-bottom: $sp-32;
}

.hero-title {
  font-size: 96rpx;
  font-weight: $fw-bold;
  color: $c-primary;
  letter-spacing: 2rpx;
}

// ── 角色卡片 ──
.role-cards {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: $sp-12;
}

.role-card {
  background: $c-surface;
  padding: $sp-24 $sp-16;
  border-radius: $r-xl;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  box-shadow: $shadow-sm;
  border: 4rpx solid transparent;
  transition: all 300ms $ease-spring;
  &:active {
    transform: scale(0.97);
  }
}

.role-card-active {
  border-color: $c-primary;
  transform: scale(1.02);
  box-shadow: $shadow-glow;
}

.role-card-icon {
  width: 96rpx;
  height: 96rpx;
  margin-bottom: $sp-8;
}

.role-card-title {
  font-size: $fs-title;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
  margin-bottom: $sp-4;
}

.role-card-desc {
  font-size: $fs-body-sm;
  color: $c-text-sub;
  line-height: $lh-relaxed;
  display: block;
  max-width: 400rpx;
}

// ── 确认按钮 ──
.confirm-area {
  margin-top: $sp-32;
  width: 100%;
  opacity: 0;
  transform: translateY(16rpx);
  transition: all 500ms $ease-out;
  pointer-events: none;
}

.confirm-area.visible {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.confirm-btn {
  width: 100%;
  background: $c-primary;
  border-radius: $r-full;
  padding: $sp-16 0;
  border: none;
  box-shadow: $shadow-glow;
  transition: all $duration-normal $ease-out;
  &:active {
    transform: scale(0.95);
  }
  &::after { border: none; }
}

.confirm-btn-text {
  font-size: $fs-subtitle;
  font-weight: $fw-medium;
  color: $c-text-inverse;
  letter-spacing: 4rpx;
}

// ── Footer ──
.role-footer {
  padding: $sp-24;
  text-align: center;
  position: relative;
  z-index: 1;
}

.footer-text {
  font-size: $fs-body-sm;
  color: $c-text-hint;
  letter-spacing: 4rpx;
}
</style>
