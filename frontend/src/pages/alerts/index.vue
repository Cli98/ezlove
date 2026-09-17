<template>
  <view class="page page-gradient">
    <!-- Header -->
    <view class="section-header">
      <image class="section-icon" src="/static/icons/notification.svg" mode="aspectFit" />
      <text class="section-title">提醒</text>
      <text class="section-subtitle">实时关注家人动态</text>
    </view>

    <!-- Loading -->
    <view v-if="alertStore.loading" class="loading-state fade-in">
      <view class="loading-dots">
        <view class="ldot" />
        <view class="ldot" />
        <view class="ldot" />
      </view>
    </view>

    <!-- Alert Cards -->
    <view v-else-if="alertStore.alerts.length > 0" class="alert-list">
      <view
        v-for="(a, index) in alertStore.alerts"
        :key="a.id"
        class="alert-card fade-in"
        :class="[
          { resolved: a.is_resolved },
          'stagger-' + Math.min(index + 1, 4)
        ]"
      >
        <!-- Left Color Bar (only for unresolved) -->
        <view
          v-if="!a.is_resolved"
          class="color-bar"
          :class="'bar-' + a.alert_level"
        />

        <view class="card-body">
          <!-- Card Header: Badge + Time -->
          <view class="card-header">
            <view class="level-badge" :class="'badge-' + a.alert_level">
              <text>{{ levelText(a.alert_level) }}</text>
            </view>
            <text class="alert-time">{{ a.created_at_text }}</text>
          </view>

          <!-- Alert Message -->
          <text class="alert-message">{{ a.message }}</text>

          <!-- Action Button (unresolved only) -->
          <view v-if="!a.is_resolved" class="alert-actions">
            <view class="resolve-btn" @tap="handleResolve(a.id)">
              <text class="resolve-btn-text">已确认安好</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Empty State -->
    <view v-else class="empty-state fade-in">
      <view class="empty-icon-circle">
        <image class="empty-icon-img" src="/static/icons/checkmark.svg" mode="aspectFit" />
      </view>
      <text class="empty-title">暂无提醒，一切安好</text>
      <view class="empty-divider" />
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onShow, onPullDownRefresh } from "@dcloudio/uni-app";
import { useAlertStore } from "@/stores/alert";
import { requestSubscribe } from "@/utils/subscribe";

const alertStore = useAlertStore();
const resolving = ref(new Set());
let subscribeRequested = false;

onShow(() => {
  alertStore.loadAlerts();
  if (!subscribeRequested) {
    subscribeRequested = true;
    requestSubscribe(['unread', 'alert']);
  }
});

onPullDownRefresh(async () => {
  try {
    await alertStore.loadAlerts();
  } finally {
    uni.stopPullDownRefresh();
  }
});

function levelText(level) {
  const map = { info: "提示", warning: "注意", urgent: "紧急" };
  return map[level] || level;
}

async function handleResolve(id) {
  if (resolving.value.has(id)) return;
  resolving.value.add(id);
  try {
    await alertStore.resolve(id);
    uni.showToast({ title: "已标记", icon: "success" });
  } catch {
    uni.showToast({ title: "操作失败", icon: "none" });
  } finally {
    resolving.value.delete(id);
  }
}
</script>

<style lang="scss" scoped>
/* Section Header */
.section-header {
  margin-bottom: $sp-32;
  margin-top: $sp-8;
}

.section-icon {
  width: 48rpx;
  height: 48rpx;
  display: block;
  margin-bottom: $sp-8;
}

.section-title {
  font-size: 56rpx;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
  margin-bottom: $sp-4;
}

.section-subtitle {
  font-size: $fs-body-sm;
  color: $c-text-hint;
  opacity: 0.8;
  display: block;
}

/* Alert List */
.alert-list {
  display: flex;
  flex-direction: column;
  gap: $sp-16;
}

/* Alert Card */
.alert-card {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-20;
  box-shadow: 0 4rpx 40rpx -4rpx rgba($c-primary, 0.05);
  border: 2rpx solid rgba($c-primary, 0.05);
  position: relative;
  overflow: hidden;
  transition: all $duration-normal $ease-out;

  &.resolved {
    background: rgba($c-surface, 0.6);
    opacity: 0.6;
  }
}

/* Left Color Bar */
.color-bar {
  position: absolute;
  top: 0;
  left: 0;
  width: 8rpx;
  height: 100%;

  &.bar-urgent {
    background: $c-error;
  }

  &.bar-warning {
    background: $c-caution;
  }

  &.bar-info {
    background: $c-info-gray;
  }
}

.card-body {
  padding-left: $sp-4;
}

/* Card Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $sp-12;
}

/* Level Badge */
.level-badge {
  padding: $sp-2 $sp-8;
  border-radius: $r-xs;
  font-size: $fs-caption;
  font-weight: $fw-bold;

  &.badge-urgent {
    background: rgba($c-error, 0.1);
    color: $c-error;
  }

  &.badge-warning {
    background: rgba($c-caution, 0.1);
    color: $c-caution;
  }

  &.badge-info {
    background: rgba($c-info-gray, 0.1);
    color: $c-info-gray;
  }
}

.alert-time {
  font-size: $fs-body-sm;
  color: rgba($c-text-hint, 0.75);
}

/* Alert Message */
.alert-message {
  font-size: 36rpx;
  font-weight: $fw-medium;
  line-height: $lh-relaxed;
  color: $c-text;
  display: block;
  margin-bottom: $sp-16;
}

/* Actions */
.alert-actions {
  display: flex;
  justify-content: flex-end;
}

.resolve-btn {
  background: $c-primary;
  padding: $sp-8 $sp-20;
  border-radius: $r-full;
  box-shadow: 0 4rpx 16rpx rgba($c-primary, 0.2);
  transition: all $duration-normal $ease-out;

  &:active {
    opacity: 0.9;
    transform: scale(0.95);
  }
}

.resolve-btn-text {
  font-size: $fs-body-sm;
  font-weight: $fw-medium;
  color: $c-text-inverse;
}

/* Empty State */
.empty-state {
  margin-top: $sp-64;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 0 $sp-40;
}

.empty-icon-circle {
  width: 180rpx;
  height: 180rpx;
  background: $gradient-warm-soft;
  border-radius: $r-full;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $sp-24;
  box-shadow: $shadow-md;
  border: 2rpx solid rgba($c-primary, 0.06);
}

.empty-icon-img {
  width: 60rpx;
  height: 60rpx;
}

.empty-title {
  font-size: 36rpx;
  color: rgba($c-text, 0.5);
  font-weight: $fw-medium;
  display: block;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding-top: 200rpx;
}

.loading-dots {
  display: flex;
  gap: $sp-12;
}

.ldot {
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

.empty-divider {
  margin-top: $sp-40;
  width: 96rpx;
  height: 2rpx;
  background: linear-gradient(90deg, transparent 0%, rgba($c-primary, 0.1) 50%, transparent 100%);
}
</style>
