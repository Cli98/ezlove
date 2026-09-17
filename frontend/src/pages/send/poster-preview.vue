<template>
  <view class="page-gradient">
    <!-- 发送成功动画 -->
    <view v-if="showSuccess" class="success-overlay">
      <view class="success-heart">
        <image class="success-heart__icon" src="/static/icons/heart-send.svg" mode="aspectFit" />
      </view>
      <text class="success-text">牵挂已送达</text>
    </view>

    <view class="preview-content">
      <view v-if="loading" class="loading-area fade-in">
        <view class="loading-poster">
          <view class="loading-shimmer" />
        </view>
        <text class="loading-text">AI 正在为您生成海报...</text>
        <view class="loading-dots">
          <view class="dot dot-1" />
          <view class="dot dot-2" />
          <view class="dot dot-3" />
        </view>
      </view>

      <view v-else class="result-area">
        <view class="poster-scroll">
          <scroll-view scroll-x class="scroll-wrap" :scroll-left="scrollLeft" scroll-with-animation>
            <view class="poster-list">
              <view
                v-for="(v, idx) in variants"
                :key="v.template_name"
                class="poster-card"
                :class="{ selected: selectedIndex === idx }"
                @tap="selectPoster(idx)"
              >
                <view v-if="idx === recommendedIndex" class="ai-badge">
                  <text>AI推荐</text>
                </view>
                <image :src="getFullUrl(v.poster_url)" mode="aspectFill" class="poster-img" />
                <text class="poster-label">{{ v.label }}</text>
              </view>
            </view>
          </scroll-view>
        </view>

        <view class="caption-section fade-in stagger-1">
          <text class="section-label">配文</text>
          <view class="caption-input-wrap">
            <textarea
              v-model="editCaption"
              :maxlength="60"
              class="caption-input"
            />
            <text class="caption-count">{{ editCaption.length }}/60</text>
          </view>
          <view v-if="captionChanged" class="refresh-row">
            <view class="refresh-btn" @tap="refreshPreview">
              <text>刷新预览</text>
            </view>
          </view>
        </view>

        <view class="bottom-actions">
          <view class="btn-secondary regenerate-btn" @tap="regenerate">换一批</view>
          <view class="btn-primary send-poster-btn" @tap="sendPoster">发送海报</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { generatePoster, renderSinglePoster } from "@/api/poster";
import { useMomentStore } from "@/stores/moment";
import { getFullUrl } from "@/api/config";

const momentStore = useMomentStore();

const loading = ref(true);
const variants = ref([]);
const selectedIndex = ref(0);
const recommendedIndex = ref(0);
const editCaption = ref("");
const originalCaption = ref("");
const scrollLeft = ref(0);
const params = ref({});
const showSuccess = ref(false);
const sending = ref(false);

const captionChanged = computed(() => editCaption.value !== originalCaption.value);

onLoad(() => {
  params.value = uni.getStorageSync("poster_params") || {};
  if (!params.value.image_url) {
    uni.showToast({ title: "参数异常", icon: "none" });
    setTimeout(() => uni.navigateBack(), 1000);
    return;
  }
  doGenerate();
});

async function doGenerate() {
  loading.value = true;
  try {
    const result = await generatePoster({
      image_url: params.value.image_url,
      user_text: params.value.user_text,
      elder_id: params.value.elder_id,
    });
    variants.value = result.variants || [];
    recommendedIndex.value = result.recommended_index || 0;
    selectedIndex.value = recommendedIndex.value;

    if (variants.value.length > 0) {
      editCaption.value = variants.value[selectedIndex.value].caption;
      originalCaption.value = editCaption.value;
    }
  } catch (e) {
    uni.showToast({ title: "生成失败，请重试", icon: "none" });
  } finally {
    loading.value = false;
  }
}

function selectPoster(idx) {
  selectedIndex.value = idx;
  editCaption.value = variants.value[idx].caption;
  originalCaption.value = editCaption.value;
}

async function refreshPreview() {
  if (!captionChanged.value) return;
  const current = variants.value[selectedIndex.value];
  uni.showLoading({ title: "重新渲染..." });
  try {
    const result = await renderSinglePoster({
      image_url: params.value.image_url,
      template_name: current.template_name,
      caption: editCaption.value,
    });
    variants.value[selectedIndex.value].poster_url = result.poster_url;
    variants.value[selectedIndex.value].caption = editCaption.value;
    originalCaption.value = editCaption.value;
    uni.showToast({ title: "已更新", icon: "success" });
  } catch (e) {
    uni.showToast({ title: "渲染失败", icon: "none" });
  } finally {
    uni.hideLoading();
  }
}

async function regenerate() {
  doGenerate();
}

async function sendPoster() {
  if (variants.value.length === 0 || sending.value) return;
  sending.value = true;
  const chosen = variants.value[selectedIndex.value];
  uni.showLoading({ title: "发送中..." });
  try {
    await momentStore.send({
      elder_id: params.value.elder_id,
      content_type: "poster",
      text_content: editCaption.value,
      media_urls: [chosen.poster_url],
      poster_meta: {
        template_name: chosen.template_name,
        original_photo: params.value.image_url,
      },
    });
    uni.hideLoading();
    uni.removeStorageSync("poster_params");
    showSuccess.value = true;
    setTimeout(() => {
      const pages = getCurrentPages();
      const delta = pages.length >= 3 ? 2 : 1;
      uni.navigateBack({ delta });
    }, 2000);
  } catch (e) {
    uni.hideLoading();
    sending.value = false;
    uni.showToast({ title: "发送失败", icon: "none" });
  }
}
</script>

<style lang="scss" scoped>
.success-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 999;
  animation: overlayIn 300ms $ease-out both;
}

.success-heart {
  width: 160rpx;
  height: 160rpx;
  border-radius: 50%;
  background: $c-surface;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 40rpx rgba(255, 140, 66, 0.35);
  animation: heartPop 600ms $ease-spring both;
  animation-delay: 150ms;
  margin-bottom: $sp-24;
}

.success-heart__icon {
  width: 80rpx;
  height: 80rpx;
}

.success-text {
  font-size: $fs-headline;
  font-weight: $fw-bold;
  color: $c-text-inverse;
  animation: textSlide 400ms $ease-out both;
  animation-delay: 400ms;
}

@keyframes overlayIn {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

@keyframes heartPop {
  0% { transform: scale(0); opacity: 0; }
  60% { transform: scale(1.15); }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes textSlide {
  0% { opacity: 0; transform: translateY(20rpx); }
  100% { opacity: 1; transform: translateY(0); }
}

.preview-content {
  padding: 0 $sp-24;
  padding-bottom: 200rpx;
}

.loading-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 120rpx;
}

.loading-poster {
  width: 400rpx;
  height: 540rpx;
  background: $c-surface;
  border-radius: $r-xl;
  overflow: hidden;
  box-shadow: $shadow-md;
  margin-bottom: $sp-32;
}

.loading-shimmer {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, $c-bg-warm 25%, $c-border-light 50%, $c-bg-warm 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.loading-text {
  font-size: $fs-body;
  color: $c-text-sub;
  margin-bottom: $sp-16;
}

.loading-dots {
  display: flex;
  gap: $sp-8;
}

.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: $c-primary-soft;
  animation: pulse 1.2s infinite;
}

.dot-2 { animation-delay: 0.2s; }
.dot-3 { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

.poster-scroll {
  margin-top: $sp-24;
}

.scroll-wrap {
  white-space: nowrap;
}

.poster-list {
  display: inline-flex;
  gap: $sp-16;
  padding: $sp-8 0 $sp-16;
}

.poster-card {
  position: relative;
  width: 320rpx;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-12;
  box-shadow: $shadow-sm;
  border: 2rpx solid rgba($c-border, 0.6);
  transition: all $duration-normal $ease-out;
  &.selected {
    border-color: $c-primary;
    box-shadow: $shadow-glow;
    transform: translateY(-8rpx);
  }
  &:active {
    transform: scale(0.97);
  }
}

.ai-badge {
  position: absolute;
  top: -12rpx;
  right: 16rpx;
  background: $gradient-warm;
  color: $c-text-inverse;
  font-size: $fs-caption;
  font-weight: $fw-bold;
  padding: 4rpx 16rpx;
  border-radius: $r-full;
  z-index: 1;
  box-shadow: 0 4rpx 12rpx rgba($c-primary, 0.3);
}

.poster-img {
  width: 296rpx;
  height: 400rpx;
  border-radius: $r-lg;
}

.poster-label {
  font-size: $fs-body-sm;
  color: $c-text-sub;
  margin-top: $sp-8;
  font-weight: $fw-medium;
}

.caption-section {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-24;
  margin-top: $sp-20;
  box-shadow: $shadow-sm;
  border: $border-subtle;
}

.section-label {
  font-size: $fs-body;
  font-weight: $fw-semibold;
  color: $c-text;
  margin-bottom: $sp-12;
  display: block;
}

.caption-input-wrap {
  position: relative;
}

.caption-input {
  width: 100%;
  min-height: 100rpx;
  font-size: $fs-body;
  line-height: $lh-relaxed;
  padding: $sp-12;
  background: $c-bg;
  border-radius: $r-md;
  border: 1rpx solid $c-border-light;
}

.caption-count {
  font-size: $fs-caption;
  color: $c-text-hint;
  text-align: right;
  display: block;
  margin-top: $sp-4;
}

.refresh-row {
  margin-top: $sp-12;
  display: flex;
  justify-content: flex-end;
}

.refresh-btn {
  padding: $sp-8 $sp-20;
  border-radius: $r-full;
  background: $c-primary-bg;
  color: $c-primary;
  font-size: $fs-body-sm;
  font-weight: $fw-semibold;
  transition: all $duration-normal $ease-out;
  &:active {
    background: $c-primary-soft;
    color: $c-text-inverse;
  }
}

.bottom-actions {
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

.regenerate-btn {
  flex: 1;
  text-align: center;
  padding: $sp-16 0;
  border-radius: $r-full;
  border: 2rpx solid $c-primary;
  color: $c-primary;
  font-size: $fs-body;
  font-weight: $fw-semibold;
  background: $c-surface;
  transition: all $duration-normal $ease-out;
  &:active {
    background: $c-primary-bg;
    transform: scale(0.97);
  }
}

.send-poster-btn {
  flex: 2;
  text-align: center;
  padding: $sp-16 0;
  border-radius: $r-full;
  background: $gradient-warm;
  color: $c-text-inverse;
  font-size: $fs-body;
  font-weight: $fw-bold;
  box-shadow: 0 6rpx 20rpx rgba($c-primary, 0.3);
  transition: all $duration-normal $ease-out;
  &:active {
    transform: scale(0.97);
    box-shadow: 0 2rpx 8rpx rgba($c-primary, 0.2);
  }
}
</style>
