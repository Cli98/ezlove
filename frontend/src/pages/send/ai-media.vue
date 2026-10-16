<template>
  <view class="ai-media-page">
    <!-- Top Bar -->
    <view class="top-bar" :style="{ ...navMetrics.barStyle, paddingRight: `${navMetrics.rightInset}px` }">
      <view class="back-btn" @tap="goBack">
        <image class="back-icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="top-bar-title app-nav-title-center" :style="navMetrics.titleStyle">AI 创作</text>
    </view>

    <view class="page-body" :style="{ paddingTop: `${navMetrics.totalHeight + 8}px` }">
      <view class="media-hero">
        <text class="media-hero__title">让照片里的回忆，\n重新有温度</text>
        <text class="media-hero__desc">选择现有能力，AI 会先生成结果供你确认</text>
      </view>
      <!-- 积分余额卡片 -->
      <view class="balance-card" v-if="balance !== null">
        <view class="balance-card__row">
          <view class="balance-card__item">
            <text class="balance-card__num">{{ balance.available_points }}</text>
            <text class="balance-card__label">可用积分</text>
          </view>
          <view class="balance-card__item">
            <text class="balance-card__num">{{ balance.total_points }}</text>
            <text class="balance-card__label">累计获得</text>
          </view>
        </view>
        <text class="balance-card__hint">发送牵挂 +5 · 查看牵挂 +2 · 每日登录 +10</text>
      </view>

      <!-- 功能选择 -->
      <view class="section-label">选择创作方式</view>

      <view class="feature-list">
        <!-- 照片生成视频 -->
        <view class="feature-card" :class="{ 'feature-card--active': selectedFeature === 'video', 'feature-card--disabled': processing }" @tap="selectFeature('video')">
          <view class="feature-card__icon feature-card__icon--video">
            <image class="feature-icon-img" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/video.png" mode="aspectFit" />
          </view>
          <view class="feature-card__body">
            <text class="feature-card__title">照片生成视频</text>
            <text class="feature-card__desc">AI 让照片动起来，给长辈一个惊喜</text>
          </view>
          <view class="feature-card__cost">
            <text class="cost-num">{{ costMap.generate_video || 50 }}</text>
            <text class="cost-label">积分</text>
          </view>
        </view>

        <!-- 老照片修复 -->
        <view class="feature-card" :class="{ 'feature-card--active': selectedFeature === 'restore', 'feature-card--disabled': processing }" @tap="selectFeature('restore')">
          <view class="feature-card__icon feature-card__icon--restore">
            <image class="feature-icon-img" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/photo-restore.png" mode="aspectFit" />
          </view>
          <view class="feature-card__body">
            <text class="feature-card__title">老照片修复</text>
            <text class="feature-card__desc">修复模糊老照片，重现珍贵记忆</text>
          </view>
          <view class="feature-card__cost">
            <text class="cost-num">{{ costMap.restore_photo || 30 }}</text>
            <text class="cost-label">积分</text>
          </view>
        </view>

        <!-- 照片动画化 -->
        <view class="feature-card" :class="{ 'feature-card--active': selectedFeature === 'animate', 'feature-card--disabled': processing }" @tap="selectFeature('animate')">
          <view class="feature-card__icon feature-card__icon--animate">
            <image class="feature-icon-img" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/sparkle.png" mode="aspectFit" />
          </view>
          <view class="feature-card__body">
            <text class="feature-card__title">照片动画化</text>
            <text class="feature-card__desc">为新照片添加动态效果，生动呈现</text>
          </view>
          <view class="feature-card__cost">
            <text class="cost-num">{{ costMap.animate_photo || 40 }}</text>
            <text class="cost-label">积分</text>
          </view>
        </view>
      </view>

      <!-- 照片选择 -->
      <view class="section-label" style="margin-top: 32rpx;">选择照片</view>
      <view class="photo-area">
        <view v-if="!localImage" class="photo-picker" @tap="choosePhoto">
          <image class="photo-picker__icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/add-photo.png" mode="aspectFit" />
          <text class="photo-picker__text">选择一张照片</text>
        </view>
        <view v-else class="photo-preview">
          <image :src="localImage" mode="aspectFill" class="photo-preview__img" />
          <view class="photo-preview__remove" @tap="localImage = ''; uploadedUrl = ''">
            <text class="remove-icon">×</text>
          </view>
          <view v-if="uploading" class="upload-overlay">
            <view class="upload-spinner" />
          </view>
        </view>
      </view>

      <!-- 风格选择（仅视频类功能） -->
      <view v-if="selectedFeature === 'video' || selectedFeature === 'animate'" class="section-label" style="margin-top: 32rpx;">
        视频风格
      </view>
      <view v-if="selectedFeature === 'video' || selectedFeature === 'animate'" class="style-chips">
        <view
          v-for="s in styleOptions"
          :key="s.value"
          class="style-chip"
          :class="{ 'style-chip--active': selectedStyle === s.value }"
          @tap="selectedStyle = s.value"
        >
          <text class="style-chip__text">{{ s.label }}</text>
        </view>
      </view>
    </view>

    <!-- 底部操作栏 -->
    <view class="bottom-bar">
      <view class="bottom-bar__inner">
        <view
          class="generate-btn"
          :class="{ 'generate-btn--disabled': !canGenerate }"
          @tap="handleGenerate"
        >
          <view v-if="processing" class="btn-spinner" />
          <text v-else class="generate-btn__text">
            {{ processing ? '生成中...' : `开始生成（${currentCost} 积分）` }}
          </text>
        </view>
      </view>
    </view>

    <!-- 错误/模型不可用弹窗 -->
    <view v-if="showError" class="modal-overlay" @tap="showError = false">
      <view class="modal-card" @tap.stop>
        <image class="modal-icon-img" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/wrench.png" mode="aspectFit" />
        <text class="modal-title">功能暂未开放</text>
        <text class="modal-desc">{{ errorMessage }}</text>
        <view class="modal-btn" @tap="showError = false">
          <text class="modal-btn__text">我知道了</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getPointBalance } from "@/api/points";
import { getAiMediaCost, generateVideo, restorePhoto, animatePhoto } from "@/api/ai-media";
import { uploadFile } from "@/api/upload";
import { useMomentStore } from "@/stores/moment";
import { getNavigationBarMetrics } from "@/utils/navigation";

const momentStore = useMomentStore();
const navMetrics = getNavigationBarMetrics();

const elderId = ref("");
const balance = ref(null);
const costMap = ref({ generate_video: 50, restore_photo: 30, animate_photo: 40 });

const selectedFeature = ref(null);
const selectedStyle = ref("default");
const localImage = ref("");
const uploadedUrl = ref("");
const uploading = ref(false);
const processing = ref(false);
const showError = ref(false);
const errorMessage = ref("");

const styleOptions = [
  { label: "温馨日常", value: "default" },
  { label: "暖光回忆", value: "warm" },
  { label: "电影质感", value: "cinematic" },
];

const currentCost = computed(() => {
  if (!selectedFeature.value) return 0;
  const map = { video: "generate_video", restore: "restore_photo", animate: "animate_photo" };
  return costMap.value[map[selectedFeature.value]] || 0;
});

const canGenerate = computed(
  () => !!selectedFeature.value && !!uploadedUrl.value && !uploading.value && !processing.value
);

onLoad((query) => {
  elderId.value = query.elderId || "";
  if (query.feature) selectedFeature.value = query.feature;
});

onMounted(async () => {
  try {
    const [bal, cost] = await Promise.all([getPointBalance(), getAiMediaCost()]);
    balance.value = bal;
    costMap.value = cost;
  } catch (e) {
    console.warn("加载积分信息失败", e);
  }
});

function selectFeature(type) {
  selectedFeature.value = type;
}

function choosePhoto() {
  uni.chooseImage({
    count: 1,
    sizeType: ["compressed"],
    success: async (res) => {
      localImage.value = res.tempFilePaths[0];
      uploading.value = true;
      try {
        const result = await uploadFile(res.tempFilePaths[0], "image");
        uploadedUrl.value = result.url;
      } catch {
        uni.showToast({ title: "照片上传失败", icon: "none" });
        localImage.value = "";
        uploadedUrl.value = "";
      } finally {
        uploading.value = false;
      }
    },
  });
}

async function handleGenerate() {
  if (!canGenerate.value) {
    if (!selectedFeature.value) {
      uni.showToast({ title: "请选择一个 AI 功能", icon: "none" });
    } else if (!uploadedUrl.value) {
      uni.showToast({ title: "请先选择一张照片", icon: "none" });
    }
    return;
  }

  // 积分不足
  if (balance.value && balance.value.available_points < currentCost.value) {
    errorMessage.value = `积分不足，需要 ${currentCost.value} 积分，当前可用 ${balance.value.available_points} 积分。多发送牵挂可以赚取积分哦！`;
    showError.value = true;
    return;
  }

  processing.value = true;

  try {
    let result;
    if (selectedFeature.value === "video") {
      result = await generateVideo(uploadedUrl.value, selectedStyle.value);
    } else if (selectedFeature.value === "restore") {
      result = await restorePhoto(uploadedUrl.value, true);
    } else if (selectedFeature.value === "animate") {
      result = await animatePhoto(uploadedUrl.value, 5);
    }

    // 如果生成成功，创建一条 care_moment
    if (result && result.result_url) {
      const contentType = selectedFeature.value === "restore" ? "image" : "video";
      await momentStore.send({
        elder_id: elderId.value,
        content_type: contentType,
        text_content: `AI ${selectedFeature.value === "video" ? "照片生成视频" : selectedFeature.value === "restore" ? "老照片修复" : "照片动画化"}`,
        media_urls: [result.result_url],
        is_ai_generated: true,
      });
      uni.showToast({ title: "生成成功，已发送", icon: "success" });
      setTimeout(() => goBack(), 1200);
    } else if (result && result.status === "processing") {
      uni.showToast({ title: "正在生成中，稍后查看", icon: "none" });
    }
  } catch (e) {
    // 解析错误
    const detail = e?.detail || e?.message || "";
    if (typeof detail === "object" && detail.code === "MODEL_NOT_AVAILABLE") {
      errorMessage.value = detail.hint || "AI 模型暂未开放，敬请期待";
      showError.value = true;
    } else if (typeof detail === "string" && detail.includes("积分不足")) {
      errorMessage.value = detail;
      showError.value = true;
    } else {
      errorMessage.value = "生成失败，积分已退还。请稍后再试。";
      showError.value = true;
    }
    // 刷新积分
    try {
      balance.value = await getPointBalance();
    } catch { /* ignore */ }
  } finally {
    processing.value = false;
  }
}

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack({ delta: 1 });
  } else {
    uni.switchTab({ url: "/pages/index/index" });
  }
}
</script>

<style lang="scss" scoped>
.ai-media-page {
  min-height: 100vh;
  background: $gradient-page;
}

// ── Top Bar ──
.top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-sizing: content-box;
  padding: 0 $sp-24;
  background: rgba($c-bg, 0.9);
  backdrop-filter: blur(24rpx);
  -webkit-backdrop-filter: blur(24rpx);
}

.back-btn {
  width: 80rpx;
  height: 80rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  &:active { opacity: 0.5; }
}

.back-icon {
  width: 34rpx;
  height: 34rpx;
}

.top-bar-title {
  font-size: $fs-title;
  font-weight: $fw-semibold;
  color: $c-text;
}

// ── Page Body ──
.page-body {
  padding-left: $sp-24;
  padding-right: $sp-24;
  padding-bottom: 280rpx;
}

.section-label {
  font-size: $fs-body-sm;
  font-weight: $fw-medium;
  color: $c-text-sub;
  margin-bottom: $sp-16;
}

// ── Balance Card ──
.balance-card {
  background: $gradient-warm;
  border-radius: $r-xl;
  padding: $sp-24;
  margin-bottom: $sp-32;
  box-shadow: $shadow-md;
}

.balance-card__row {
  display: flex;
  gap: $sp-32;
  margin-bottom: $sp-12;
}

.balance-card__item {
  display: flex;
  flex-direction: column;
}

.balance-card__num {
  font-size: $fs-subtitle;
  font-weight: $fw-bold;
  color: $c-text-inverse;
}

.balance-card__label {
  font-size: $fs-caption;
  color: rgba(255, 255, 255, 0.75);
  margin-top: $sp-2;
}

.balance-card__hint {
  font-size: $fs-caption;
  color: rgba(255, 255, 255, 0.65);
}

// ── Feature Cards ──
.feature-list {
  display: flex;
  flex-direction: row;
  gap: 14rpx;
}

.feature-card {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  padding: 22rpx 10rpx;
  background: $c-surface;
  border-radius: $r-xl;
  box-shadow: $shadow-xs;
  border: 2rpx solid rgba($c-border, 0.3);
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.98);
    border-color: $c-primary;
  }

  &--active {
    border-color: $c-primary;
    background: $c-primary-surface;
    box-shadow: 0 8rpx 24rpx rgba($c-primary, 0.12);
  }

  &--disabled {
    opacity: 0.5;
    pointer-events: none;
  }
}

.feature-card__icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: $r-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feature-card__icon--video { background: rgba($c-primary, 0.1); }
.feature-card__icon--restore { background: rgba($c-safe, 0.1); }
.feature-card__icon--animate { background: rgba($c-accent, 0.1); }

.feature-icon-img {
  width: 40rpx;
  height: 40rpx;
}

.feature-card__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.feature-card__title {
  font-size: 25rpx;
  font-weight: $fw-semibold;
  color: $c-text;
}

.feature-card__desc {
  display: none;
  color: $c-text-sub;
  margin-top: $sp-2;
}

.feature-card__cost {
  display: flex;
  flex-direction: row;
  gap: 4rpx;
  align-items: center;
  flex-shrink: 0;
  min-width: 80rpx;
}

.cost-num {
  font-size: 25rpx;
  font-weight: $fw-bold;
  color: $c-accent;
}

.cost-label {
  font-size: 21rpx;
  color: $c-text-hint;
}

// ── Photo Picker ──
.photo-area {
  width: 100%;
}

.photo-picker {
  width: 100%;
  height: 320rpx;
  border-radius: $r-xl;
  border: 3rpx dashed $c-border;
  background: rgba($c-surface, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $sp-8;

  &:active {
    background: rgba($c-border, 0.08);
  }
}

.photo-picker__icon {
  width: 64rpx;
  height: 64rpx;
}

.photo-picker__text {
  font-size: $fs-body-sm;
  color: $c-text-sub;
}

.photo-preview {
  position: relative;
  width: 100%;
  height: 400rpx;
  border-radius: $r-xl;
  overflow: hidden;
  box-shadow: $shadow-sm;
}

.photo-preview__img {
  width: 100%;
  height: 100%;
}

.photo-preview__remove {
  position: absolute;
  top: $sp-12;
  right: $sp-12;
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-icon {
  color: #fff;
  font-size: $fs-body;
}

.upload-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-spinner {
  width: 56rpx;
  height: 56rpx;
  border: 4rpx solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

// ── Style Chips ──
.style-chips {
  display: flex;
  gap: $sp-12;
  margin-bottom: $sp-32;
}

.style-chip {
  padding: $sp-10 $sp-24;
  border-radius: $r-full;
  border: 2rpx solid $c-border;
  background: transparent;
  transition: all $duration-normal $ease-out;

  &:active { transform: scale(0.97); }

  &--active {
    background: $c-primary;
    border-color: $c-primary;

    .style-chip__text { color: $c-text-inverse; }
  }
}

.style-chip__text {
  font-size: $fs-body-sm;
  color: $c-text-sub;
  white-space: nowrap;
}

// ── Bottom Bar ──
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  padding: $sp-16 $sp-24;
  padding-bottom: calc(#{$sp-32} + env(safe-area-inset-bottom));
  background: rgba($c-bg, 0.7);
  backdrop-filter: blur(40rpx);
  -webkit-backdrop-filter: blur(40rpx);
  border-radius: $r-xl $r-xl 0 0;
  border-top: 1rpx solid rgba($c-border, 0.4);
}

.bottom-bar__inner {
  display: flex;
}

.generate-btn {
  flex: 1;
  height: 96rpx;
  border-radius: $r-full;
  background: $c-primary;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 24rpx rgba($c-primary, 0.2);
  transition: all $duration-normal $ease-out;

  &:active { transform: scale(0.97); }

  &--disabled {
    opacity: 0.45;
    box-shadow: none;
  }
}

.generate-btn__text {
  font-size: $fs-body;
  font-weight: $fw-bold;
  color: $c-text-inverse;
  letter-spacing: 2rpx;
}

.btn-spinner {
  width: 40rpx;
  height: 40rpx;
  border: 4rpx solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}

// ── Modal ──
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $sp-48;
}

.modal-card {
  width: 100%;
  max-width: 560rpx;
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-40 $sp-32;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: $shadow-xl;
}

.modal-icon-img {
  width: 72rpx;
  height: 72rpx;
  margin-bottom: $sp-16;
  opacity: 0.6;
}

.modal-title {
  font-size: $fs-subtitle;
  font-weight: $fw-bold;
  color: $c-text;
  margin-bottom: $sp-12;
}

.modal-desc {
  font-size: $fs-body-sm;
  color: $c-text-sub;
  text-align: center;
  line-height: $lh-relaxed;
  margin-bottom: $sp-24;
}

.modal-btn {
  padding: $sp-12 $sp-48;
  background: $c-primary;
  border-radius: $r-full;
}

.modal-btn__text {
  font-size: $fs-body-sm;
  font-weight: $fw-bold;
  color: $c-text-inverse;
}
</style>

<style lang="scss" scoped>
.ai-media-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 90% 8%, rgba($c-accent,.12), transparent 23%),
    $gradient-page;
}
.top-bar { background: rgba($c-bg,.92); }
.top-bar-title { color: $c-text; font-family: "Songti SC", "STSong", serif; font-size: 36rpx; font-weight: 800; }
.back-btn { width: 76rpx; height: 76rpx; }
.back-icon { width: 34rpx; height: 34rpx; }
.page-body { padding-left: $sp-24; padding-right: $sp-24; padding-bottom: 210rpx; }
.media-hero { margin: 26rpx 8rpx 32rpx; }
.media-hero__title {
  display: block;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 50rpx;
  font-weight: 900;
  line-height: 1.22;
  white-space: pre-line;
}
.media-hero__desc { display: block; margin-top: 10rpx; color: $c-text-sub; font-size: 27rpx; }
.balance-card { border: 1rpx solid rgba($c-border,.7); border-radius: 26rpx; background: rgba(255,255,255,.75); box-shadow: $shadow-sm; }
.section-label { margin: 30rpx 4rpx 16rpx; color: $c-text; font-family: "Songti SC", "STSong", serif; font-size: 32rpx; letter-spacing: 0; }
.feature-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14rpx; }
.feature-card {
  min-height: 218rpx;
  padding: 20rpx 10rpx 16rpx;
  flex-direction: column;
  justify-content: flex-start;
  text-align: center;
  border: 2rpx solid transparent;
  border-radius: 24rpx;
  background: rgba(255,255,255,.8);
  box-shadow: $shadow-sm;
}
.feature-card--active { border-color: $c-primary; background: $c-primary-surface; box-shadow: 0 10rpx 26rpx rgba($c-primary,.12); }
.feature-card__icon { width: 66rpx; height: 66rpx; margin: 0 0 10rpx; }
.feature-icon-img { width: 38rpx; height: 38rpx; }
.feature-card__body { width: 100%; }
.feature-card__title { display: block; font-family: "Songti SC", "STSong", serif; font-size: 26rpx; font-weight: 800; white-space: nowrap; }
.feature-card__desc { display: none; }
.feature-card__cost { margin-top: 8rpx; display: flex; flex-direction: row; align-items: baseline; gap: 4rpx; }
.cost-num { font-size: 24rpx; color: $c-primary; }
.cost-label { font-size: 21rpx; }
.photo-area { border-radius: 28rpx; overflow: hidden; }
.photo-picker { min-height: 360rpx; border-radius: 28rpx; border-color: $c-border; background: rgba(255,255,255,.72); }
.photo-preview { height: 430rpx; border-radius: 28rpx; box-shadow: $shadow-md; }
.style-chip { border-radius: $r-full; background: rgba(255,255,255,.8); }
.style-chip--active { background: $c-primary-surface; border-color: $c-primary; }
.bottom-bar { background: rgba($c-bg,.94); border-top-color: rgba($c-border,.7); backdrop-filter: blur(24rpx); }
.generate-btn { min-height: 94rpx; border-radius: $r-full; background: $gradient-warm; box-shadow: $shadow-glow; }
</style>
