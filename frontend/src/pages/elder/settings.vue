<template>
  <view class="settings-page">
    <view class="settings-nav" :style="navMetrics.barStyle">
      <view class="settings-nav__back" @tap="goBack">
        <image src="/static/icons/arrow-back.svg" mode="aspectFit" />
      </view>
      <text class="settings-nav__title app-nav-title-center" :style="navMetrics.titleStyle">提醒设置</text>
    </view>
    <view class="settings-heading">
      <text class="settings-heading__title">合适的提醒，\n让关心成为一种习惯</text>
      <text class="settings-heading__subtitle">设置未读多久后提醒你</text>
    </view>
    <view class="settings-card fade-in">
      <view class="setting-row">
        <view class="setting-left">
          <image class="setting-icon" src="/static/icons/clock.svg" mode="aspectFit" />
          <text class="setting-label">未读提醒时间</text>
        </view>
        <picker :value="thresholdIndex" :range="thresholdOptions" :disabled="saving" @change="onThresholdChange">
          <view class="picker-trigger" :class="{ 'picker-trigger--disabled': saving }">
            <text class="picker-value">{{ saving ? '保存中...' : thresholdOptions[thresholdIndex] }}</text>
            <text class="picker-arrow">›</text>
          </view>
        </picker>
      </view>
    </view>

    <view class="settings-note">
      <image src="/static/icons/sun.svg" mode="aspectFit" />
      <text>提醒是为了及时问候，不代表家人遇到危险。</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { updateRelation } from "@/api/relation";
import { getNavigationBarMetrics } from "@/utils/navigation";

const relationId = ref("");
const thresholdIndex = ref(2);
const thresholdOptions = ["6小时", "8小时", "12小时", "24小时"];
const thresholdValues = [6, 8, 12, 24];
const saving = ref(false);
const navMetrics = getNavigationBarMetrics();

function goBack() {
  uni.navigateBack();
}

onLoad((query) => {
  relationId.value = query.relationId;
  if (query.threshold) {
    const idx = thresholdValues.indexOf(Number(query.threshold));
    if (idx >= 0) thresholdIndex.value = idx;
  }
});

async function onThresholdChange(e) {
  const prevIndex = thresholdIndex.value;
  thresholdIndex.value = e.detail.value;
  saving.value = true;
  try {
    await updateRelation(relationId.value, {
      alert_threshold: thresholdValues[thresholdIndex.value],
    });
    uni.showToast({ title: "已保存", icon: "success" });
  } catch (err) {
    thresholdIndex.value = prevIndex;
    uni.showToast({ title: "保存失败", icon: "none" });
  } finally {
    saving.value = false;
  }
}
</script>

<style lang="scss" scoped>
.settings-page {
  min-height: 100vh;
  padding: 0 28rpx calc(48rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background:
    radial-gradient(circle at 12% 92%, rgba($c-accent, 0.08), transparent 24%),
    $c-bg;
}

.settings-nav {
  box-sizing: content-box;
  position: relative;
  margin: 0 -28rpx;

  &__back {
    width: 72rpx;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  &__title { color: $c-text; font-family: "Songti SC", "STSong", serif; font-size: 36rpx; font-weight: 800; }
  image { width: 34rpx; height: 34rpx; }
}

.settings-heading { padding: 32rpx 12rpx 42rpx; }
.settings-heading__title {
  display: block;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 50rpx;
  font-weight: 900;
  line-height: 1.24;
  white-space: pre-line;
}
.settings-heading__subtitle { display: block; margin-top: 8rpx; color: $c-text-sub; font-size: 28rpx; }

.settings-card {
  background: $c-surface;
  border-radius: $r-xl;
  padding: 20rpx 32rpx;
  box-shadow: $shadow-md;
  border: $border-subtle;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 112rpx;
  padding: 16rpx 0;
}

.settings-note {
  display: flex;
  align-items: flex-start;
  gap: 18rpx;
  margin-top: 28rpx;
  padding: 28rpx;
  border-radius: 24rpx;
  color: $c-text-sub;
  background: rgba(255, 255, 255, 0.6);
  font-size: 26rpx;
  line-height: 1.7;

  image { width: 38rpx; height: 38rpx; flex: none; }
}

.setting-left {
  display: flex;
  align-items: center;
  gap: $sp-12;
}

.setting-icon {
  width: 40rpx;
  height: 40rpx;
}

.setting-label {
  font-size: $fs-body;
  font-weight: $fw-medium;
  color: $c-text;
}

.picker-trigger {
  display: flex;
  align-items: center;
  gap: $sp-8;
  padding: $sp-8 $sp-16;
  background: $c-primary-bg;
  border-radius: $r-full;
  box-shadow: 0 2rpx 8rpx rgba($c-primary, 0.1);
  transition: all $duration-normal $ease-out;

  &--disabled {
    opacity: 0.5;
    pointer-events: none;
  }
}

.picker-value {
  font-size: $fs-body;
  color: $c-primary;
  font-weight: $fw-semibold;
}

.picker-arrow {
  font-size: $fs-subtitle;
  color: $c-primary;
}
</style>
