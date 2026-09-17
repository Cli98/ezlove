<template>
  <view class="page">
    <!-- 子女端：生成邀请码发给老人 -->
    <view v-if="!userStore.isElder" class="invite-section fade-in">
      <view class="section-icon-wrap">
        <image class="section-icon-img" src="/static/icons/invite.svg" mode="aspectFit" />
      </view>
      <text class="section-title">邀请家人加入</text>
      <text class="section-desc">生成邀请码，让老人或其他家人输入即可绑定</text>

      <view v-if="inviteCode" class="code-display">
        <text class="code-value">{{ inviteCode }}</text>
        <view class="btn-primary copy-btn" @tap="copyCode">复制邀请码</view>
      </view>
      <view v-else class="generate-area">
        <view class="btn-primary generate-btn" @tap="generate">生成邀请码</view>
      </view>
    </view>

    <!-- 双方都能输入邀请码绑定 -->
    <view class="bind-section fade-in" :class="userStore.isElder ? '' : 'stagger-1'">
      <view class="section-icon-wrap small">
        <image class="section-icon-img" src="/static/icons/key.svg" mode="aspectFit" />
      </view>
      <text class="section-title">{{ userStore.isElder ? '绑定家人' : '我有邀请码' }}</text>
      <text v-if="userStore.isElder" class="section-desc">输入子女发给你的邀请码</text>
      <view class="input-wrap">
        <input
          v-model="inputCode"
          type="text"
          placeholder="输入邀请码"
          class="code-input"
          :adjust-position="true"
          maxlength="20"
        />
      </view>
      <view class="btn-primary bind-btn" @tap="handleBind">绑定</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { useUserStore } from "@/stores/user";
import { useRelationStore } from "@/stores/relation";

const userStore = useUserStore();
const relationStore = useRelationStore();
const inviteCode = ref("");
const inputCode = ref("");
const generating = ref(false);
const binding = ref(false);

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
.invite-section, .bind-section {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-40 $sp-32;
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
  font-size: $fs-title;
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
  background: $c-primary-bg;
  border-radius: $r-lg;
}

.copy-btn {
  width: 100%;
}

.generate-area {
  margin-top: $sp-8;
}

.generate-btn {
  width: 100%;
}

.input-wrap {
  margin: $sp-24 0;
}

.code-input {
  width: 100%;
  height: 88rpx;
  box-sizing: border-box;
  text-align: center;
  font-size: $fs-title;
  letter-spacing: 8rpx;
  padding: $sp-20;
  background: $c-bg;
  border-radius: $r-lg;
  border: $border-subtle;
  transition: border-color $duration-normal $ease-out;
}

.bind-btn {
  width: 100%;
}
</style>
