<template>
  <view class="page page-gradient">
    <!-- Loading -->
    <view v-if="momentStore.loading" class="loading-center fade-in">
      <view class="loading-dot-wrap">
        <view class="loading-dot" />
        <view class="loading-dot" />
        <view class="loading-dot" />
      </view>
    </view>

    <!-- Empty State -->
    <view v-else-if="momentStore.moments.length === 0" class="empty-state fade-in">
      <view class="empty-icon-wrap">
        <image class="empty-icon" src="/static/icons/edit-note.svg" mode="aspectFit" />
      </view>
      <text class="empty-title">{{ userStore.isElder ? '还没有收到牵挂' : '第一份牵挂从这里开始' }}</text>
      <text class="empty-desc">{{ userStore.isElder ? '家人正在想你呢，耐心等等~' : '一句简单的问候，也能让家人感到温暖' }}</text>
      <view v-if="!userStore.isElder" class="btn-primary empty-btn" @tap="goSend">发送第一条</view>
    </view>

    <!-- History List -->
    <view v-else class="history-content">
      <!-- Section Header -->
      <view class="section-header">
        <view class="section-header-row">
          <image class="section-icon" src="/static/icons/edit-note.svg" mode="aspectFit" />
          <view>
            <text class="section-title">{{ userStore.isElder ? '收到的牵挂' : '记录' }}</text>
            <text class="section-subtitle">{{ userStore.isElder ? '家人们的每一份心意' : '珍惜每一次跨越距离的叮嘱' }}</text>
          </view>
        </view>
      </view>

      <!-- Cards -->
      <view class="card-list">
        <view
          v-for="(m, index) in momentStore.moments"
          :key="m.id"
          class="history-card fade-in"
          :class="['stagger-' + Math.min(index + 1, 4), { unread: !m.is_read }]"
          @tap="goViewDetail(m)"
        >
          <!-- Card Header: Avatar + Name/Status + Time -->
          <view class="card-header">
            <view class="card-header-left">
              <view class="avatar-wrap" :class="{ 'avatar-unread': !m.is_read, 'avatar-read': m.is_read }">
                <image
                  v-if="m.elder_avatar"
                  :src="getFullUrl(m.elder_avatar)"
                  mode="aspectFill"
                  class="avatar-img"
                />
                <text v-else class="avatar-initial">{{ (m.elder_nickname || m.elder_label || '家')[0] }}</text>
              </view>
              <view class="name-status">
                <text class="elder-name">{{ m.elder_nickname || m.elder_label || '家人' }}</text>
                <view class="status-row">
                  <view class="status-dot" :class="m.is_read ? 'dot-read' : 'dot-unread'" />
                  <text class="status-text" :class="m.is_read ? 'text-read' : 'text-unread'">
                    {{ m.is_read ? '已读' : '未读' }}
                  </text>
                </view>
              </view>
            </view>
            <text class="card-time">{{ formatTime(m.created_at) }}</text>
          </view>

          <!-- Message Preview -->
          <view v-if="m.content_type === 'poster' && m.media_urls?.length" class="poster-thumb-row">
            <image :src="getFullUrl(m.media_urls[0])" mode="aspectFill" class="poster-thumb" />
            <text class="poster-tag">海报</text>
          </view>
          <text v-else class="message-preview">{{ m.text_content }}</text>

          <!-- Footer: Dashed Divider + Action -->
          <view class="card-footer">
            <view v-if="!m.is_read" class="footer-action" @tap="goViewDetail(m)">
              <text class="action-text action-primary">查看详情</text>
              <text class="action-arrow">›</text>
            </view>
            <view v-else class="footer-action">
              <text class="action-text action-muted">已存入存档</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Bottom Hint -->
      <view class="bottom-hint">
        <text class="bottom-hint-text">没有更多历史记录了</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onShow, onPullDownRefresh } from "@dcloudio/uni-app";
import { useMomentStore } from "@/stores/moment";
import { useUserStore } from "@/stores/user";
import { formatRelativeTime } from "@/utils/date";
import { getFullUrl } from "@/api/config";

const momentStore = useMomentStore();
const userStore = useUserStore();

function formatTime(isoStr) {
  return formatRelativeTime(isoStr);
}

onShow(() => {
  momentStore.loadMoments();
});

onPullDownRefresh(async () => {
  try {
    await momentStore.loadMoments();
  } finally {
    uni.stopPullDownRefresh();
  }
});

function goSend() {
  uni.navigateTo({ url: "/pages/send/index" });
}

function goViewDetail(m) {
  uni.navigateTo({ url: `/pages/view/detail?id=${m.id}` });
}
</script>

<style lang="scss" scoped>
/* Loading */
.loading-center {
  display: flex;
  justify-content: center;
  padding-top: 200rpx;
}

.loading-dot-wrap {
  display: flex;
  gap: $sp-12;
}

.loading-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: $c-primary;
  animation: dotPulse 1.2s ease-in-out infinite;
  &:nth-child(2) { animation-delay: 200ms; }
  &:nth-child(3) { animation-delay: 400ms; }
}

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.empty-icon-wrap {
  width: 120rpx;
  height: 120rpx;
  background: $c-primary-bg;
  border-radius: $r-2xl;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $sp-24;
}

.empty-icon {
  width: 56rpx;
  height: 56rpx;
}

.empty-title {
  font-size: $fs-subtitle;
  font-weight: $fw-semibold;
  color: $c-text;
  display: block;
}

.empty-desc {
  font-size: $fs-body;
  color: $c-text-sub;
  margin-top: $sp-8;
  display: block;
}

.empty-btn {
  margin-top: $sp-32;
  padding: $sp-16 $sp-48;
}

/* Section Header */
.section-header {
  margin-bottom: $sp-32;
}

.section-header-row {
  display: flex;
  align-items: center;
  gap: $sp-16;
}

.section-icon {
  width: 48rpx;
  height: 48rpx;
}

.section-title {
  font-size: 56rpx;
  font-weight: $fw-bold;
  color: $c-text;
  letter-spacing: -2rpx;
  display: block;
  margin-bottom: $sp-4;
}

.section-subtitle {
  font-size: $fs-body-sm;
  color: $c-text-hint;
  display: block;
}

/* Card List */
.card-list {
  display: flex;
  flex-direction: column;
  gap: $sp-16;
}

/* History Card */
.history-card {
  background: $c-surface;
  border-radius: $r-2xl;
  padding: $sp-20;
  box-shadow: $shadow-md;
  border: 2rpx solid rgba($c-border, 0.3);
  transition: transform $duration-normal $ease-out;
  position: relative;
  overflow: hidden;

  &:active {
    transform: scale(0.98);
  }

  &.unread {
    border-left: 6rpx solid $c-primary;
    box-shadow: $shadow-md, 0 0 0 2rpx rgba($c-primary, 0.06);
  }
}

/* Card Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $sp-12;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: $sp-12;
}

.avatar-wrap {
  width: 96rpx;
  height: 96rpx;
  border-radius: $r-full;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $c-primary-bg;

  &.avatar-unread {
    border: 4rpx solid rgba($c-primary, 0.1);
  }

  &.avatar-read {
    border: 4rpx solid rgba($c-safe, 0.1);
  }
}

.avatar-img {
  width: 100%;
  height: 100%;
}

.avatar-initial {
  font-size: $fs-title;
  font-weight: $fw-bold;
  color: $c-primary;
}

.name-status {
  display: flex;
  flex-direction: column;
}

.elder-name {
  font-size: 36rpx;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
}

.status-row {
  display: flex;
  align-items: center;
  gap: $sp-6;
  margin-top: $sp-2;
}

.status-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: $r-full;

  &.dot-unread {
    background: $c-primary;
    box-shadow: 0 0 0 4rpx $c-bg, 0 0 0 6rpx rgba($c-primary, 0.2);
  }

  &.dot-read {
    background: $c-safe;
  }
}

.status-text {
  font-size: $fs-caption;
  font-weight: $fw-medium;

  &.text-unread {
    color: $c-primary;
  }

  &.text-read {
    color: $c-text-hint;
  }
}

.card-time {
  font-size: $fs-caption;
  color: $c-text-hint;
  font-weight: $fw-medium;
  background: $c-bg-warm;
  padding: $sp-2 $sp-8;
  border-radius: $r-full;
}

/* Message Preview */
.message-preview {
  font-size: 30rpx;
  line-height: $lh-relaxed;
  color: rgba($c-text, 0.8);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Poster Thumbnail */
.poster-thumb-row {
  display: flex;
  align-items: center;
  gap: $sp-12;
}

.poster-thumb {
  width: 120rpx;
  height: 160rpx;
  border-radius: $r-md;
  box-shadow: $shadow-sm;
  border: $border-subtle;
}

.poster-tag {
  font-size: $fs-body-sm;
  color: $c-primary;
  background: $c-primary-bg;
  padding: $sp-4 $sp-12;
  border-radius: $r-full;
  font-weight: $fw-medium;
}

/* Card Footer */
.card-footer {
  margin-top: $sp-16;
  padding-top: $sp-12;
  border-top: 2rpx dashed rgba($c-text, 0.05);
  display: flex;
  justify-content: flex-end;
}

.footer-action {
  display: flex;
  align-items: center;
  gap: $sp-4;
}

.action-text {
  font-size: $fs-caption;
  font-weight: $fw-bold;
}

.action-primary {
  color: $c-primary;
}

.action-muted {
  color: $c-text-hint;
}

.action-arrow {
  font-size: $fs-body-sm;
  color: $c-primary;
  font-weight: $fw-bold;
}

/* Bottom Hint */
.bottom-hint {
  margin-top: $sp-48;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.bottom-hint-text {
  font-size: $fs-caption;
  color: rgba($c-text-hint, 0.4);
}
</style>
