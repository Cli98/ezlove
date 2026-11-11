<template>
  <view class="phrase-page">
    <view class="top-bar" :style="{ ...navMetrics.barStyle, paddingRight: `${navMetrics.rightInset}px` }">
      <view class="back-btn" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="top-bar__title app-nav-title-center" :style="navMetrics.titleStyle">推荐话术</text>
    </view>

    <view class="page-body" :style="{ paddingTop: `${navMetrics.totalHeight + 12}px` }">
      <view class="header-area fade-in">
        <text class="page-title">挑一句，改成自己的话</text>
        <text class="page-desc">这些是家人们常说的话，选中后还可以再改</text>
      </view>

      <scroll-view class="tab-bar" scroll-x :show-scrollbar="false">
        <view
          v-for="group in PHRASE_GROUPS"
          :key="group.key"
          class="tab-item"
          :class="{ 'tab-item--active': activeKey === group.key }"
          @tap="switchGroup(group.key)"
        >
          <text>{{ group.label }}</text>
        </view>
      </scroll-view>

      <view class="phrase-list">
        <view
          v-for="(item, index) in currentItems"
          :key="`${activeKey}-${index}`"
          class="phrase-card"
          :class="{ 'phrase-card--selected': selectedIndex === index }"
          @tap="selectedIndex = index"
        >
          <text class="phrase-text">{{ item }}</text>
          <text class="phrase-action">{{ selectedIndex === index ? "✓ 已选" : "选这句" }}</text>
        </view>
      </view>
    </view>

    <view class="bottom-bar">
      <view class="use-btn" :class="{ 'use-btn--disabled': selectedIndex < 0 }" @tap="usePhrase">
        <text>用这句话</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { getNavigationBarMetrics } from "@/utils/navigation";
import { PHRASE_GROUPS } from "@/utils/phrases";

const navMetrics = getNavigationBarMetrics();
const activeKey = ref(PHRASE_GROUPS[0].key);
const selectedIndex = ref(-1);

const currentItems = computed(
  () => PHRASE_GROUPS.find((group) => group.key === activeKey.value)?.items || []
);

function switchGroup(key) {
  if (activeKey.value === key) return;
  activeKey.value = key;
  selectedIndex.value = -1;
}

// 回填到发送页，由发送页 onShow 读取后清空
function usePhrase() {
  if (selectedIndex.value < 0) {
    uni.showToast({ title: "先选一句吧", icon: "none" });
    return;
  }
  uni.setStorageSync("phrase_text", currentItems.value[selectedIndex.value]);
  uni.navigateBack();
}

function goBack() {
  uni.navigateBack();
}
</script>

<style lang="scss" scoped>
.phrase-page { min-height: 100vh; background: $gradient-page; }
.top-bar { position: fixed; inset: 0 0 auto; z-index: 50; display: flex; align-items: center; box-sizing: content-box; background: rgba($c-bg, 0.94); backdrop-filter: blur(20rpx); }
.back-btn { width: 88rpx; height: 100%; display: flex; align-items: center; justify-content: center; image { width: 34rpx; height: 34rpx; } }
.top-bar__title { font-family: "Songti SC", "STSong", serif; font-size: 36rpx; font-weight: 800; color: $c-text; }
.page-body { padding-left: $sp-24; padding-right: $sp-24; padding-bottom: 190rpx; }

.header-area { padding: $sp-24 0 $sp-16; }
.page-title {
  font-family: "Songti SC", "STSong", serif;
  font-size: 50rpx;
  font-weight: 900;
  line-height: 1.25;
  color: $c-text;
  display: block;
}
.page-desc { font-size: $fs-body; color: $c-text-sub; margin-top: $sp-8; display: block; }

.tab-bar { white-space: nowrap; margin: $sp-16 -$sp-24 $sp-20; padding: 0 $sp-24; }
.tab-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 64rpx;
  padding: 0 $sp-32;
  margin-right: $sp-12;
  border-radius: $r-full;
  border: 2rpx solid $c-border;
  background: rgba(255, 255, 255, 0.72);
  color: $c-text-sub;
  font-size: $fs-body-sm;
  transition: all $duration-normal $ease-out;
}
.tab-item--active {
  border-color: transparent;
  background: $gradient-warm;
  color: $c-text-inverse;
  font-weight: $fw-semibold;
  box-shadow: $shadow-sm;
}

.phrase-card {
  background: rgba(255, 255, 255, 0.86);
  border-radius: $r-xl;
  padding: $sp-24;
  margin-bottom: $sp-16;
  box-shadow: $shadow-md;
  border: $border-subtle;
  transition: all $duration-normal $ease-out;
  &:active { transform: scale(0.98); }
}
.phrase-card--selected {
  border-color: $c-primary;
  background: linear-gradient(135deg, #fffaf6, $c-primary-bg);
}
.phrase-text { font-size: 31rpx; line-height: $lh-relaxed; color: $c-text; display: block; }
.phrase-action {
  display: block;
  margin-top: $sp-12;
  text-align: right;
  font-size: $fs-caption;
  color: $c-primary;
  font-weight: $fw-semibold;
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
.use-btn {
  flex: 1;
  min-height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $r-lg;
  font-size: $fs-body;
  font-weight: $fw-semibold;
  color: $c-text-inverse;
  background: $gradient-warm;
  box-shadow: $shadow-glow;
}
.use-btn--disabled { opacity: 0.42; box-shadow: none; }
</style>