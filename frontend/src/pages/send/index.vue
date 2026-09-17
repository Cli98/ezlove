<template>
  <view class="send-page">
    <!-- TopAppBar -->
    <view class="top-app-bar">
      <view class="top-app-bar__status-spacer" />
      <view class="top-app-bar__content">
        <view class="top-app-bar__nav" @tap="uni.navigateBack()">
          <text class="nav-icon">‹</text>
        </view>
        <text class="top-app-bar__title">发送牵挂</text>
        <view class="top-app-bar__right" />
      </view>
    </view>

    <view class="page-body">
      <!-- Recipient Selection -->
      <view class="section fade-in">
        <text class="section__label">发送给</text>
        <view v-if="!relationStore.relations.length && !relationStore.loading" class="no-relation-hint">
          <text class="no-relation-text">还没有绑定家人</text>
          <view class="no-relation-link" @tap="uni.navigateTo({ url: '/pages/bind/invite' })">
            <text class="no-relation-link-text">去邀请绑定 →</text>
          </view>
        </view>
        <scroll-view v-else scroll-x class="chips-scroll">
          <view class="chips-row">
            <view
              v-for="r in relationStore.relations"
              :key="r.id"
              class="recipient-chip"
              :class="{ 'recipient-chip--active': selectedElderId === r.elder_user_id }"
              @tap="selectedElderId = r.elder_user_id"
            >
              <text class="recipient-chip__label">{{ r.relation_label || '家人' }}</text>
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- Text Input -->
      <view class="section fade-in stagger-1">
        <view class="text-card">
          <textarea
            v-model="textContent"
            placeholder="今天想和Ta说点什么..."
            :maxlength="200"
            class="text-card__input"
            placeholder-class="text-card__placeholder"
          />
          <view class="text-card__footer">
            <text
              class="text-card__counter"
              :class="{ 'text-card__counter--max': textContent.length >= 200 }"
            >{{ textContent.length }}/200</text>
          </view>
        </view>
      </view>

      <!-- Image Upload -->
      <view class="section fade-in stagger-2">
        <view class="image-grid">
          <!-- Add Image Button -->
          <view class="image-add-wrap">
            <view class="image-add" @tap="chooseImage">
              <text class="image-add__icon">+</text>
              <text class="image-add__label">添加照片</text>
            </view>
          </view>
          <!-- Image Preview -->
          <view v-if="imageUrl" class="image-item-wrap">
            <view class="image-preview">
              <image :src="imageUrl" mode="aspectFill" class="image-preview__img" />
              <view v-if="uploading" class="upload-overlay">
                <view class="upload-spinner" />
              </view>
              <view
                v-else
                class="image-preview__remove"
                @tap.stop="imageUrl = ''; uploadedUrl = ''"
              >
                <text class="remove-icon">×</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- Info Cards (Bento) -->
      <view class="bento-grid fade-in stagger-3">
        <view class="bento-card bento-card--amber">
          <image class="bento-card__icon" src="/static/icons/sun.svg" mode="aspectFit" />
          <view class="bento-card__body">
            <text class="bento-card__hint">{{ timeOfDayHint }}</text>
            <text class="bento-card__value">{{ timeOfDayValue }}</text>
          </view>
        </view>
        <view class="bento-card bento-card--sage">
          <image class="bento-card__icon" src="/static/icons/clock.svg" mode="aspectFit" />
          <view class="bento-card__body">
            <text class="bento-card__hint">发送小贴士</text>
            <text class="bento-card__value">{{ sendTip }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- Bottom Action Bar -->
    <view class="bottom-bar">
      <view class="bottom-bar__inner">
        <!-- AI Assist Button -->
        <view
          class="action-btn action-btn--outline"
          @tap="uni.navigateTo({ url: `/pages/send/ai-suggest?elderId=${selectedElderId}` })"
        >
          <image class="action-btn__sparkle" src="/static/icons/sparkle.svg" mode="aspectFit" />
          <text class="action-btn__text">AI 帮我写</text>
        </view>
        <!-- AI Media Button -->
        <view
          class="action-btn action-btn--outline action-btn--accent"
          @tap="uni.navigateTo({ url: `/pages/send/ai-media?elderId=${selectedElderId}` })"
        >
          <image class="action-btn__icon-img" src="/static/icons/video.svg" mode="aspectFit" />
          <text class="action-btn__text">AI 创作</text>
        </view>
        <!-- Send Button -->
        <view
          class="action-btn action-btn--primary"
          :class="{ 'action-btn--disabled': !canGenerate }"
          @tap="handleGenerate"
        >
          <text class="action-btn__text">发送牵挂</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useRelationStore } from "@/stores/relation";
import { useMomentStore } from "@/stores/moment";
import { uploadImage } from "@/api/upload";
import { requestSubscribe } from "@/utils/subscribe";

const relationStore = useRelationStore();
const momentStore = useMomentStore();

const selectedElderId = ref("");
const textContent = ref("");
const imageUrl = ref("");
const uploadedUrl = ref("");
const uploading = ref(false);
const sending = ref(false);

const canGenerate = computed(
  () => (!!uploadedUrl.value || !!textContent.value.trim()) && !!selectedElderId.value && !uploading.value && !sending.value
);

const timeOfDayHint = computed(() => {
  const h = new Date().getHours();
  if (h < 9) return "早晨好";
  if (h < 12) return "上午好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
});

const timeOfDayValue = computed(() => {
  const h = new Date().getHours();
  if (h < 9) return "分享一张早餐照片吧";
  if (h < 12) return "拍张照片问候长辈";
  if (h < 14) return "午后正好发一条牵挂";
  if (h < 18) return "今天过得怎么样？";
  return "晚间适合发温馨问候";
});

const sendTip = computed(() => {
  const tips = ["照片比文字更有温度", "一张生活照就是最好的问候", "长辈最爱看日常小事"];
  const idx = new Date().getDate() % tips.length;
  return tips[idx];
});

onMounted(async () => {
  await relationStore.loadRelations();
  if (relationStore.relations.length > 0) {
    selectedElderId.value = relationStore.relations[0].elder_user_id;
  }
});

onShow(() => {
  const aiText = uni.getStorageSync("ai_suggest_text");
  if (aiText) {
    textContent.value = aiText;
    uni.removeStorageSync("ai_suggest_text");
  }
});

function chooseImage() {
  uni.chooseImage({
    count: 1,
    sizeType: ["compressed"],
    success: async (res) => {
      imageUrl.value = res.tempFilePaths[0];
      uploading.value = true;
      try {
        uploadedUrl.value = await uploadImage(res.tempFilePaths[0]);
      } catch (e) {
        uni.showToast({ title: "图片上传失败", icon: "none" });
        imageUrl.value = "";
        uploadedUrl.value = "";
      } finally {
        uploading.value = false;
      }
    },
  });
}

async function handleGenerate() {
  if (!canGenerate.value) {
    if (!selectedElderId.value) {
      uni.showToast({ title: "选择要分享给谁", icon: "none" });
    } else {
      uni.showToast({ title: "写点文字或选张照片吧", icon: "none" });
    }
    return;
  }

  if (uploadedUrl.value) {
    uni.setStorageSync("poster_params", {
      image_url: uploadedUrl.value,
      user_text: textContent.value || null,
      elder_id: selectedElderId.value,
    });
    requestSubscribe(['unread']);
    uni.navigateTo({ url: "/pages/send/poster-preview" });
  } else {
    sending.value = true;
    try {
      await momentStore.send({
        elder_id: selectedElderId.value,
        content_type: "text",
        text_content: textContent.value.trim(),
      });
      requestSubscribe(['unread']);
      uni.showToast({ title: "已发送", icon: "success" });
      textContent.value = "";
      setTimeout(() => uni.navigateBack(), 1200);
    } catch {
      uni.showToast({ title: "发送失败", icon: "none" });
    } finally {
      sending.value = false;
    }
  }
}
</script>

<style lang="scss" scoped>
// ── TopAppBar — 固定顶部，毛玻璃效果 ──
.top-app-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background: rgba($c-bg, 0.8);
  backdrop-filter: blur(24rpx);
  -webkit-backdrop-filter: blur(24rpx);
}

.top-app-bar__status-spacer {
  // 适配状态栏高度
  height: var(--status-bar-height, 50rpx);
}

.top-app-bar__content {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding: 0 $sp-16;
}

.top-app-bar__nav {
  width: 80rpx;
  height: 80rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  &:active {
    opacity: 0.5;
  }
}

.nav-icon {
  font-size: 40rpx;
  color: $c-text-sub;
  font-weight: $fw-regular;
}

.top-app-bar__title {
  flex: 1;
  text-align: center;
  font-size: $fs-title;
  font-weight: $fw-semibold;
  color: $c-text;
}

.top-app-bar__right {
  width: 80rpx;
}

// ── Page Layout ──
.send-page {
  min-height: 100vh;
  background: $gradient-page;
}

.page-body {
  // 状态栏 + 导航栏 + 间距
  padding-top: calc(var(--status-bar-height, 50rpx) + 88rpx + #{$sp-32});
  padding-left: $sp-24;
  padding-right: $sp-24;
  padding-bottom: 260rpx;
}

// ── Section ──
.section {
  margin-bottom: $sp-32;
}

.section__label {
  display: block;
  font-size: $fs-body-sm;
  font-weight: $fw-medium;
  color: $c-text-sub;
  margin-bottom: $sp-16;
}

// ── 无绑定提示 ──
.no-relation-hint {
  display: flex;
  align-items: center;
  gap: $sp-12;
  padding: $sp-16;
  background: $c-warn-bg;
  border-radius: $r-lg;
  border: 2rpx solid $c-warn-soft;
}

.no-relation-text {
  font-size: $fs-body;
  color: $c-text-sub;
  flex: 1;
}

.no-relation-link {
  padding: $sp-6 $sp-16;
  background: $c-primary;
  border-radius: $r-full;
}

.no-relation-link-text {
  font-size: $fs-body-sm;
  color: $c-text-inverse;
  font-weight: $fw-bold;
  white-space: nowrap;
}

// ── Recipient Chips — 水平滚动选择器 ──
.chips-scroll {
  white-space: nowrap;
  width: 100%;
  ::-webkit-scrollbar {
    display: none;
  }
}

.chips-row {
  display: inline-flex;
  gap: $sp-12;
  padding-bottom: $sp-8;
}

.recipient-chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: $sp-10 $sp-24;
  border-radius: $r-full;
  border: 2rpx solid $c-border;
  background: transparent;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.97);
  }
}

.recipient-chip__label {
  font-size: $fs-body-sm;
  color: $c-text-sub;
  white-space: nowrap;
}

.recipient-chip--active {
  background: $c-primary;
  border-color: $c-primary;
  box-shadow: $shadow-sm, 0 4rpx 16rpx rgba($c-primary, 0.15);

  .recipient-chip__label {
    color: $c-text-inverse;
    font-weight: $fw-bold;
  }
}

// ── Text Card — 白色卡片输入区 ──
.text-card {
  position: relative;
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-24;
  box-shadow: $shadow-xs;
  border: 2rpx solid rgba($c-border, 0.3);
}

.text-card__input {
  width: 100%;
  height: 300rpx;
  font-size: $fs-body;
  line-height: $lh-relaxed;
  color: $c-text;
  background: transparent;
  border: none;
  padding: 0;
}

.text-card__placeholder {
  color: $c-text-hint;
}

.text-card__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: $sp-8;
}

.text-card__counter {
  font-size: $fs-caption;
  color: $c-text-hint;
  font-family: "SF Mono", "Menlo", "Courier New", monospace;

  &--max {
    color: $c-primary;
  }
}

// ── Image Grid — 三列方格 ──
.image-grid {
  display: flex;
  flex-wrap: wrap;
  gap: $sp-12;
}

.image-add-wrap,
.image-item-wrap {
  // 三列等宽，减去间距
  width: calc((100% - #{$sp-12} * 2) / 3);
}

.image-add {
  width: 100%;
  padding-top: 100%; // 1:1 正方形
  position: relative;
  border-radius: $r-xl;
  border: 3rpx dashed $c-border;
  background: rgba($c-surface, 0.5);
  overflow: hidden;
  transition: all $duration-normal $ease-out;

  &:active {
    background: rgba($c-border, 0.08);
    transform: scale(0.97);
  }
}

.image-add__icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -70%);
  font-size: 56rpx;
  color: $c-primary;
  line-height: 1;
}

.image-add__label {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, 40%);
  font-size: $fs-caption;
  color: $c-text-sub;
  letter-spacing: 2rpx;
  white-space: nowrap;
}

.image-preview {
  width: 100%;
  padding-top: 100%;
  position: relative;
  border-radius: $r-xl;
  overflow: hidden;
  box-shadow: $shadow-sm;
}

.image-preview__img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.upload-spinner {
  width: 56rpx;
  height: 56rpx;
  border: 4rpx solid rgba(255, 255, 255, 0.3);
  border-top-color: $c-text-inverse;
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.image-preview__remove {
  position: absolute;
  top: 8rpx;
  right: 8rpx;
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10rpx);
  -webkit-backdrop-filter: blur(10rpx);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.remove-icon {
  color: $c-text-inverse;
  font-size: $fs-body-sm;
  line-height: 1;
}

// ── Bento Info Cards ──
.bento-grid {
  display: flex;
  gap: $sp-12;
  margin-bottom: $sp-40;
}

.bento-card {
  flex: 1;
  padding: $sp-20;
  border-radius: $r-xl;
  display: flex;
  flex-direction: column;
  box-shadow: $shadow-sm;
}

.bento-card--amber {
  background: rgba($c-accent, 0.1);
  border: 2rpx solid rgba($c-accent, 0.2);
}

.bento-card--sage {
  background: rgba($c-safe, 0.1);
  border: 2rpx solid rgba($c-safe, 0.2);
}

.bento-card__icon {
  width: 48rpx;
  height: 48rpx;
  margin-bottom: $sp-12;
}

.bento-card__body {
  display: flex;
  flex-direction: column;
  gap: $sp-2;
}

.bento-card__hint {
  font-size: $fs-caption;
  color: $c-text-sub;
  line-height: $lh-tight;
}

.bento-card__value {
  font-size: $fs-caption;
  color: $c-text;
  font-weight: $fw-medium;
  line-height: $lh-tight;
}

// ── Bottom Action Bar — 固定底部，毛玻璃 ──
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
  gap: $sp-16;
}

// ── Action Buttons ──
.action-btn {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  height: 96rpx;
  border-radius: $r-full;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.97);
  }
}

.action-btn--outline {
  flex: 1;
  border: 2rpx solid $c-primary;
  background: transparent;

  &:active {
    background: rgba($c-primary, 0.05);
  }
}

.action-btn--accent {
  border-color: $c-accent;

  &:active {
    background: rgba($c-accent, 0.05);
  }

  .action-btn__text {
    color: $c-accent;
  }
}

.action-btn__icon-img {
  width: 32rpx;
  height: 32rpx;
  margin-right: $sp-4;
}

.action-btn--primary {
  flex: 1.5;
  background: $c-primary;
  border: none;
  box-shadow: 0 8rpx 24rpx rgba($c-primary, 0.2);
}

.action-btn--disabled {
  opacity: 0.45;
  box-shadow: none;
}

.action-btn__sparkle {
  width: 32rpx;
  height: 32rpx;
  margin-right: $sp-8;
}

.action-btn__text {
  font-size: $fs-body-sm;
  font-weight: $fw-semibold;
  letter-spacing: 2rpx;

  .action-btn--outline & {
    color: $c-primary;
  }

  .action-btn--primary & {
    color: $c-text-inverse;
    font-weight: $fw-bold;
    letter-spacing: 4rpx;
  }
}
</style>
