<template>
  <view class="ai-page">
    <view class="top-bar" :style="{ ...navMetrics.barStyle, paddingRight: `${navMetrics.rightInset}px` }">
      <view class="back-btn" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="top-bar__title app-nav-title-center" :style="navMetrics.titleStyle">AI 帮我写</text>
    </view>

    <view class="page-body" :style="{ paddingTop: `${navMetrics.totalHeight + 12}px` }">
    <view class="header-area fade-in">
      <text class="page-title">把想说的话变得更温暖</text>
      <text class="page-desc">AI 已根据家人的近况准备了这些问候</text>
      <image class="header-mark" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/brand/logo-mark.png" mode="aspectFit" />
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
          <text class="select-copy">{{ selectedIndex === index ? '✓ 已选择' : '使用这句话' }}</text>
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
      <view class="refresh-btn" @tap="regenerate">↻ 换一批</view>
      <view class="use-btn" @tap="useSuggestion">✓ 使用这句话</view>
    </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getAiSuggestions } from "@/api/ai";
import { getNavigationBarMetrics } from "@/utils/navigation";

const elderId = ref("");
const suggestions = ref([]);
const selectedIndex = ref(0);
const loading = ref(false);
const navMetrics = getNavigationBarMetrics();

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

function goBack() {
  uni.navigateBack();
}
</script>

<style lang="scss" scoped>
.ai-page { min-height: 100vh; background: $gradient-page; }
.top-bar { position: fixed; inset: 0 0 auto; z-index: 50; display: flex; align-items: center; box-sizing: content-box; background: rgba($c-bg, 0.94); backdrop-filter: blur(20rpx); }
.back-btn { width: 88rpx; height: 100%; display: flex; align-items: center; justify-content: center; image { width: 34rpx; height: 34rpx; } }
.top-bar__title { font-family: "Songti SC", "STSong", serif; font-size: 36rpx; font-weight: 800; color: $c-text; }
.page-body { padding-left: $sp-24; padding-right: $sp-24; padding-bottom: 190rpx; }
.header-area {
  position: relative;
  padding: $sp-24 120rpx $sp-24 0;
  margin-bottom: $sp-20;
}

.page-title {
  font-family: "Songti SC", "STSong", serif;
  font-size: 50rpx;
  font-weight: 900;
  line-height: 1.25;
  color: $c-text;
  display: block;
}
.header-mark { position: absolute; top: 0; right: 0; width: 130rpx; height: 130rpx; opacity: 0.16; }

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
  background: rgba(255, 255, 255, 0.86);
  border-radius: $r-xl;
  padding: $sp-24;
  margin-bottom: $sp-16;
  box-shadow: $shadow-md;
  border: $border-subtle;
  transition: all $duration-normal $ease-out;
  &.selected {
    border-color: $c-primary;
    background: linear-gradient(135deg, #fffaf6, $c-primary-bg);
    box-shadow: $shadow-md;
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
.select-copy { font-size: $fs-caption; color: $c-primary; font-weight: $fw-semibold; }

.suggestion-text {
  font-size: 31rpx;
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
  background: rgba($c-bg, 0.96);
  box-shadow: $shadow-md;
  border-top: $border-subtle;
}
.refresh-btn, .use-btn { min-height: 88rpx; display: flex; align-items: center; justify-content: center; border-radius: $r-lg; font-size: $fs-body; font-weight: $fw-semibold; }
.refresh-btn { flex: 1; color: $c-text-sub; border: 2rpx solid $c-border; background: rgba(255,255,255,.72); }
.use-btn { flex: 1.2; color: $c-text-inverse; background: $gradient-warm; box-shadow: $shadow-glow; }
</style>
