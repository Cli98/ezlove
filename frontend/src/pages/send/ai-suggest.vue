<template>
  <view class="page">
    <view class="header-area fade-in">
      <text class="page-title">AI 帮你写牵挂</text>
      <text class="page-desc">选一条合适的，或者修改后发送</text>
    </view>

    <view v-if="loading" class="loading-state fade-in">
      <view class="loading-dot-wrap">
        <view class="loading-dot" />
        <view class="loading-dot" />
        <view class="loading-dot" />
      </view>
      <text class="loading-text">正在为您生成...</text>
    </view>

    <view v-else-if="suggestions.length > 0" class="suggestion-list">
      <view
        v-for="(item, index) in suggestions"
        :key="index"
        class="suggestion-card fade-in"
        :class="[{ selected: selectedIndex === index }, 'stagger-' + (index + 1)]"
        @tap="selectedIndex = index"
      >
        <view class="suggestion-tag-row">
          <text class="suggestion-tag">{{ item.tag }}</text>
          <view v-if="selectedIndex === index" class="check-mark">
            <image class="check-icon-img" src="/static/icons/checkmark.svg" mode="aspectFit" />
          </view>
        </view>
        <text class="suggestion-text">{{ item.text }}</text>
      </view>
    </view>

    <view v-else class="empty-state">
      <text class="empty-text">AI 暂时无法生成建议</text>
      <view class="retry-btn" @tap="loadSuggestions">
        <text class="retry-btn-text">重新生成</text>
      </view>
    </view>

    <view class="bottom-bar">
      <view class="btn-secondary refresh-btn" @tap="regenerate">换一批</view>
      <view class="btn-primary use-btn" @tap="useSuggestion">使用这条</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getAiSuggestions } from "@/api/ai";

const elderId = ref("");
const suggestions = ref([]);
const selectedIndex = ref(0);
const loading = ref(false);

onLoad((query) => {
  elderId.value = query.elderId;
  loadSuggestions();
});

async function loadSuggestions() {
  loading.value = true;
  try {
    const res = await getAiSuggestions(elderId.value);
    suggestions.value = res.suggestions || [];
    selectedIndex.value = 0;
  } catch (e) {
    uni.showToast({ title: "生成失败，请重试", icon: "none" });
  } finally {
    loading.value = false;
  }
}

function regenerate() {
  if (loading.value) return;
  loadSuggestions();
}

function useSuggestion() {
  if (suggestions.value.length === 0) return;
  const selected = suggestions.value[selectedIndex.value];
  uni.setStorageSync("ai_suggest_text", selected.text);
  uni.navigateBack();
}
</script>

<style lang="scss" scoped>
.header-area {
  padding-top: $sp-24;
  margin-bottom: $sp-32;
}

.page-title {
  font-size: $fs-headline;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
}

.page-desc {
  font-size: $fs-body;
  color: $c-text-sub;
  margin-top: $sp-8;
  display: block;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 160rpx;
}

.loading-dot-wrap {
  display: flex;
  gap: $sp-12;
  margin-bottom: $sp-24;
}

.loading-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: $gradient-warm;
  box-shadow: 0 2rpx 8rpx rgba($c-primary, 0.3);
  animation: dotPulse 1.2s ease-in-out infinite;
  &:nth-child(2) { animation-delay: 200ms; }
  &:nth-child(3) { animation-delay: 400ms; }
}

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

.loading-text {
  font-size: $fs-body;
  color: $c-text-hint;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 160rpx;
}

.empty-text {
  font-size: $fs-body;
  color: $c-text-hint;
  display: block;
  margin-bottom: $sp-24;
}

.retry-btn {
  padding: $sp-12 $sp-40;
  background: $c-primary;
  border-radius: $r-full;
  box-shadow: $shadow-sm;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.95);
  }
}

.retry-btn-text {
  font-size: $fs-body;
  font-weight: $fw-semibold;
  color: $c-text-inverse;
}

.suggestion-card {
  background: $c-surface;
  border-radius: $r-lg;
  padding: $sp-24;
  margin-bottom: $sp-16;
  box-shadow: $shadow-md;
  border: $border-subtle;
  transition: all $duration-normal $ease-out;
  &.selected {
    border-color: $c-primary;
    background: $c-primary-surface;
    box-shadow: $shadow-glow;
    border-left: 6rpx solid $c-primary;
  }
  &:active {
    transform: scale(0.98);
    transition-timing-function: $ease-spring;
  }
}

.suggestion-tag-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $sp-12;
}

.suggestion-tag {
  font-size: $fs-body-sm;
  color: $c-primary;
  background: $c-primary-bg;
  padding: $sp-4 $sp-16;
  border-radius: $r-full;
  font-weight: $fw-medium;
  box-shadow: 0 0 0 4rpx rgba($c-primary, 0.06);
}

.check-mark {
  width: 40rpx;
  height: 40rpx;
  background: $gradient-warm;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 12rpx rgba($c-primary, 0.3);
}

.check-icon-img {
  width: 24rpx;
  height: 24rpx;
}

.suggestion-text {
  font-size: $fs-body;
  line-height: $lh-relaxed;
  color: $c-text;
  display: block;
}

.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: $sp-16;
  padding: $sp-24;
  padding-bottom: calc(#{$sp-24} + env(safe-area-inset-bottom));
  background: $c-surface;
  box-shadow: $shadow-md;
  border-top: $border-subtle;
}

.refresh-btn {
  flex: 1;
}

.use-btn {
  flex: 2;
}
</style>
