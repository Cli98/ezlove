<template>
  <view class="page">
    <view class="settings-card fade-in">
      <text class="settings-title">提醒设置</text>
      <text class="settings-desc">设置未读多久后提醒你</text>

      <view class="divider" />

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
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { updateRelation } from "@/api/relation";

const relationId = ref("");
const thresholdIndex = ref(2);
const thresholdOptions = ["6小时", "8小时", "12小时", "24小时"];
const thresholdValues = [6, 8, 12, 24];
const saving = ref(false);

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
.settings-card {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-32;
  box-shadow: $shadow-md;
  border: $border-subtle;
}

.settings-title {
  font-size: $fs-title;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
}

.settings-desc {
  font-size: $fs-body;
  color: $c-text-sub;
  margin-top: $sp-4;
  display: block;
}

.divider {
  height: 1rpx;
  background: $gradient-divider;
  margin: $sp-24 0;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $sp-16 0;
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
