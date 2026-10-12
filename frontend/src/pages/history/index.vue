<template>
  <view class="page page-gradient">
    <view class="history-hero">
      <text class="history-hero__title">{{ heroTitle }}</text>
      <text class="history-hero__desc">{{ heroDescription }}</text>
    </view>

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
      <view class="history-summary">
        <text>{{ userStore.isElder ? '家人们的每一份心意' : '珍惜每一次跨越距离的叮嘱' }}</text>
        <text>{{ momentStore.moments.length }} 条</text>
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
                <image v-if="participantAvatar(m, index)" :src="participantAvatar(m, index)" mode="aspectFill" class="avatar-img" />
                <text v-else class="avatar-initial">{{ participantName(m)[0] || '家' }}</text>
              </view>
              <view class="name-status">
                <text class="elder-name">{{ participantName(m) }}</text>
                <view class="status-row">
                  <view class="status-dot" :class="m.is_read ? 'dot-read' : 'dot-unread'" />
                  <text class="status-text" :class="m.is_read ? 'text-read' : 'text-unread'">
                    {{ readStatus(m) }}
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
              <text class="action-text action-primary">{{ userStore.isElder ? '查看牵挂' : '查看详情' }}</text>
              <text class="action-arrow">›</text>
            </view>
            <view v-else class="footer-action">
              <text class="action-text action-muted">{{ userStore.isElder ? '已查看' : '已存入存档' }}</text>
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
import { computed } from "vue";
import { onShow, onPullDownRefresh } from "@dcloudio/uni-app";
import { useMomentStore } from "@/stores/moment";
import { useUserStore } from "@/stores/user";
import { formatRelativeTime } from "@/utils/date";
import { getFullUrl } from "@/api/config";
import { getElderAvatar } from "@/utils/avatar";

const momentStore = useMomentStore();
const userStore = useUserStore();
const heroTitle = computed(() => userStore.isElder ? "家人的每一句牵挂，\n都在这里" : "每一次问候，\n都有回音");
const heroDescription = computed(() => userStore.isElder ? "慢慢看，每一句都是家人的惦念" : "用一条牵挂，拉近心的距离");

function participantName(moment) {
  return userStore.isElder ? (moment.sender_name || "家人") : (moment.elder_name || "家人");
}

function participantAvatar(moment, index) {
  const avatar = userStore.isElder ? moment.sender_avatar_url : moment.elder_avatar_url;
  if (avatar) return getFullUrl(avatar);
  return userStore.isElder ? "" : getElderAvatar(moment, index);
}

function readStatus(moment) {
  if (userStore.isElder) return moment.is_read ? "已查看" : "待查看";
  return moment.is_read ? "已读" : "未读";
}

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
  padding-top: $sp-24;
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
  background: rgba(255, 255, 255, 0.86);
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

<style lang="scss" scoped>
.page {
  padding-top: calc(var(--status-bar-height, 50rpx) + 96rpx);
  background:
    radial-gradient(circle at 92% 7%, rgba($c-accent,.10), transparent 23%),
    $gradient-page;
}
.history-hero { margin: 0 8rpx 34rpx; }
.history-hero__title {
  display: block;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 56rpx;
  font-weight: 900;
  line-height: 1.2;
  white-space: pre-line;
}
.history-hero__desc { display: block; margin-top: 10rpx; color: $c-text-sub; font-size: 28rpx; }
.history-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18rpx;
  padding: 0 6rpx;
  color: $c-text-hint;
  font-size: 25rpx;
}
.card-list { gap: 16rpx; }
.history-card {
  padding: 24rpx;
  border: 1rpx solid rgba($c-border,.76);
  border-radius: 26rpx;
  background: rgba(255,255,255,.82);
  box-shadow: $shadow-sm;
}
.history-card.unread { border-color: rgba($c-primary,.3); box-shadow: 0 10rpx 30rpx rgba($c-primary,.08); }
.avatar-wrap { width: 88rpx; height: 88rpx; box-shadow: none; }
.elder-name { font-family: "Songti SC", "STSong", serif; font-size: 34rpx; font-weight: 800; }
.message-preview { margin: 20rpx 0 10rpx; padding: 20rpx; border-radius: 18rpx; background: $c-bg; color: $c-text; font-size: 29rpx; line-height: 1.65; }
.poster-thumb { border-radius: 18rpx; }
.card-footer { border-color: $c-border-light; }
.action-primary { color: $c-primary; }
.empty-state { padding-top: 70rpx; }
</style>
