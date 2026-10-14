<template>
  <view class="invite-page">
    <view class="invite-nav" :style="navMetrics.barStyle">
      <view class="invite-nav__back" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="app-nav-title-center" :style="navMetrics.titleStyle">邀请家人加入</text>
    </view>

    <view class="invite-body">
    <!-- 子女端：生成邀请码发给老人 -->
    <view v-if="!userStore.isElder" class="invite-section fade-in">
      <view class="section-icon-wrap">
        <image class="section-icon-img" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/invite.png" mode="aspectFit" />
      </view>
      <text class="section-title">邀请家人加入</text>
      <text class="section-desc">生成邀请码，让老人或其他家人输入即可绑定</text>

      <view v-if="inviteCode" class="code-display">
        <text class="code-value">{{ inviteCode }}</text>
        <view class="btn-primary copy-btn" @tap="copyCode">复制邀请码</view>
        <text class="regenerate" @tap="generate">重新生成</text>
      </view>
      <view v-else class="generate-area">
        <view class="btn-primary generate-btn" @tap="generate">生成邀请码</view>
      </view>
    </view>

    <!-- 双方都能输入邀请码绑定 -->
    <view class="bind-section fade-in" :class="userStore.isElder ? '' : 'stagger-1'">
      <view class="section-icon-wrap small">
        <image class="section-icon-img" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/key.png" mode="aspectFit" />
      </view>
      <text class="section-title">{{ userStore.isElder ? '绑定家人' : '我有邀请码' }}</text>
      <text v-if="userStore.isElder" class="section-desc">输入子女发给你的邀请码</text>
      <view class="input-wrap">
        <input
          v-model="inputCode"
          type="text"
          placeholder="输入邀请码"
          placeholder-class="code-input-placeholder"
          class="code-input"
          :adjust-position="true"
          maxlength="20"
        />
      </view>
      <text class="paste-hint" @tap="pasteCode">复制了邀请码？点此粘贴</text>
      <view class="btn-primary bind-btn" @tap="handleBind">绑定</view>
    </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";
import { useRelationStore } from "@/stores/relation";
import { getNavigationBarMetrics } from "@/utils/navigation";

const userStore = useUserStore();
const relationStore = useRelationStore();
const inviteCode = ref("");
const inputCode = ref("");
const generating = ref(false);
const binding = ref(false);
const navMetrics = getNavigationBarMetrics();

function goBack() {
  uni.navigateBack();
}

// 长辈视角只需输入邀请码，标题与入口文案保持一致
onShow(() => {
  uni.setNavigationBarTitle({ title: userStore.isElder ? "绑定家人" : "邀请绑定" });
});

async function generate() {
  if (generating.value) return;
  generating.value = true;
  try {
    const res = await relationStore.generateInvite();
    inviteCode.value = res.invite_code;
  } catch (e) {
    uni.showToast({ title: "生成失败", icon: "none" });
  } finally {
    generating.value = false;
  }
}

function copyCode() {
  uni.setClipboardData({ data: inviteCode.value });
}

function pasteCode() {
  uni.getClipboardData({
    success: ({ data }) => {
      const code = (data || "").trim();
      if (code) inputCode.value = code;
      else uni.showToast({ title: "剪贴板为空", icon: "none" });
    },
    fail: () => uni.showToast({ title: "读取剪贴板失败", icon: "none" }),
  });
}

async function handleBind() {
  const code = inputCode.value.trim()
  if (!code) {
    uni.showToast({ title: "请输入邀请码", icon: "none" });
    return;
  }
  if (binding.value) return;
  binding.value = true;
  try {
    await relationStore.bind(code);
    uni.showToast({ title: "绑定成功", icon: "success" });
    setTimeout(() => uni.navigateBack(), 1500);
  } catch (e) {
    uni.showToast({ title: e.message || "绑定失败，请检查邀请码", icon: "none" });
  } finally {
    binding.value = false;
  }
}
</script>

<style lang="scss" scoped>
.invite-page {
  min-height: 100vh;
  padding-bottom: calc(48rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background:
    radial-gradient(circle at 8% 16%, rgba($c-primary-soft, 0.08), transparent 26%),
    $c-bg;
}

.invite-nav {
  box-sizing: content-box;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  position: relative;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 36rpx;
  font-weight: 800;

  &__back {
    width: 72rpx;
    height: 100%;
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  image { width: 34rpx; height: 34rpx; }
}

.invite-body { padding: 34rpx 28rpx 0; }

.invite-section, .bind-section {
  background: rgba(255, 255, 255, 0.86);
  border-radius: 32rpx;
  padding: 40rpx 32rpx;
  margin-bottom: $sp-24;
  box-shadow: $shadow-md;
  border: $border-subtle;
  text-align: center;
}

.section-icon-wrap {
  width: 100rpx;
  height: 100rpx;
  background: $gradient-warm-soft;
  border-radius: $r-2xl;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto $sp-20;
  box-shadow: $shadow-sm;
  &.small {
    width: 80rpx;
    height: 80rpx;
  }
}

.section-icon-img {
  width: 48rpx;
  height: 48rpx;
}

.section-title {
  font-family: "Songti SC", "STSong", serif;
  font-size: 40rpx;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
  margin-bottom: $sp-8;
}

.section-desc {
  font-size: $fs-body;
  color: $c-text-sub;
  display: block;
  margin-bottom: $sp-32;
}

.code-display {
  margin-top: $sp-24;
}

.code-value {
  font-size: $fs-display;
  font-weight: $fw-bold;
  color: $c-primary;
  letter-spacing: 16rpx;
  display: block;
  margin-bottom: $sp-32;
  padding: $sp-24;
  background: linear-gradient(135deg, #FFF7F2, $c-primary-bg);
  border-radius: $r-lg;
}

.copy-btn {
  width: 100%;
}

.regenerate {
  display: block;
  margin-top: 22rpx;
  color: $c-text-hint;
  font-size: 25rpx;
}

.generate-area {
  margin-top: $sp-8;
}

.generate-btn {
  width: 100%;
}

.input-wrap {
  margin: $sp-24 0 $sp-8;
}

.paste-hint {
  display: block;
  margin-bottom: $sp-24;
  color: $c-primary;
  font-size: $fs-body-sm;
  text-decoration: underline;
}

.code-input {
  width: 100%;
  height: 88rpx;
  box-sizing: border-box;
  text-align: center;
  font-size: $fs-title;
  letter-spacing: 8rpx;
  line-height: 88rpx;
  padding: 0 $sp-20;
  background: $c-bg;
  border-radius: $r-lg;
  border: $border-subtle;
  transition: border-color $duration-normal $ease-out;
}

.code-input-placeholder {
  letter-spacing: 2rpx;
}

.bind-btn {
  width: 100%;
}
</style>
