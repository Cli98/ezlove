<template>
  <view class="page-gradient">
    <view v-if="loading" class="loading-center">
      <view class="loading-dots">
        <view class="ld-dot" />
        <view class="ld-dot" />
        <view class="ld-dot" />
      </view>
    </view>
    <view v-else class="status-content">
      <view class="status-header fade-in">
        <view class="elder-avatar-lg">
          <text class="avatar-letter">{{ elderName[0] || '家' }}</text>
        </view>
        <text class="elder-name">{{ elderName }}</text>
      </view>

      <view class="status-card fade-in stagger-1" :class="todayRead ? 'safe' : 'warn'">
        <view class="status-indicator">
          <view class="status-dot" :class="todayRead ? 'active' : 'inactive'" />
          <text class="status-label">{{ todayRead ? '今日已查看' : '今日未查看' }}</text>
        </view>
        <text class="last-time">{{ lastActiveText }}</text>

        <view v-if="!todayRead" class="checkin-area">
          <view class="checkin-btn" @tap="handleCheckin">
            <text>今天和Ta在一起，标记已守护</text>
          </view>
        </view>
      </view>

      <!-- 暂停提醒 -->
      <view class="pause-card fade-in stagger-2">
        <view class="pause-header">
          <view class="pause-left">
            <image class="pause-icon" src="/static/icons/clock.svg" mode="aspectFit" />
            <view class="pause-info">
              <text class="pause-title">暂停提醒</text>
              <text class="pause-desc">{{ pausedUntil ? '提醒已暂停至 ' + formatDate(pausedUntil) : '老人有事时可暂停几天' }}</text>
            </view>
          </view>
        </view>
        <view v-if="pausedUntil" class="pause-actions">
          <view class="pause-resume-btn" @tap="resumeAlert">恢复提醒</view>
        </view>
        <view v-else class="pause-actions">
          <view class="pause-option" @tap="pauseAlert(3)">
            <text>暂停 3 天</text>
          </view>
          <view class="pause-option" @tap="pauseAlert(7)">
            <text>暂停 7 天</text>
          </view>
          <view class="pause-option" @tap="pauseAlert(14)">
            <text>暂停 14 天</text>
          </view>
        </view>
      </view>

      <!-- 提醒设置入口 -->
      <view v-if="relationId" class="settings-entry fade-in stagger-3" @tap="goSettings">
        <view class="settings-left">
          <view class="settings-icon-badge">
            <text class="settings-icon-text">设</text>
          </view>
          <view class="settings-info">
            <text class="settings-title">提醒设置</text>
            <text class="settings-desc">调整未读提醒时间阈值</text>
          </view>
        </view>
        <text class="settings-arrow">›</text>
      </view>

      <view class="week-card fade-in stagger-4">
        <text class="section-label">最近 7 天</text>
        <view class="calendar-row">
          <view v-for="(day, idx) in weekDays" :key="day.date" class="day-cell">
            <text class="day-label">{{ day.label }}</text>
            <view
              class="day-ring"
              :class="day.active ? 'active' : 'inactive'"
              :style="day.active ? `animation-delay: ${idx * 100}ms` : ''"
            >
              <view v-if="day.active" class="day-fill" :style="`animation-delay: ${idx * 100 + 150}ms`" />
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getElderStatus, getElderActivity, manualCheckin } from "@/api/elder";
import { updateRelation, getRelations } from "@/api/relation";

const elderId = ref("");
const elderName = ref("家人");
const todayRead = ref(false);
const lastActiveText = ref("暂无记录");
const pausedUntil = ref(null);
const weekDays = ref([]);
const relationId = ref("");
const alertThreshold = ref(null);
const loading = ref(true);
const submitting = ref(false);

onLoad((query) => {
  elderId.value = query.id;
  loadData();
});

async function loadData() {
  try {
    const [status, activity, relations] = await Promise.all([
      getElderStatus(elderId.value),
      getElderActivity(elderId.value, { days: 7 }),
      getRelations(),
    ]);
    elderName.value = status.elder_name || "家人";
    todayRead.value = status.today_read;
    lastActiveText.value = status.last_active_text || "暂无记录";
    pausedUntil.value = status.alert_paused_until || null;
    weekDays.value = activity.days || [];

    const rel = relations.find((r) => r.elder_user_id === elderId.value);
    if (rel) {
      relationId.value = rel.id;
      alertThreshold.value = rel.alert_threshold ?? null;
    }
  } catch (e) {
    uni.showToast({ title: "加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
}

async function handleCheckin() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    await manualCheckin(elderId.value);
    todayRead.value = true;
    uni.showToast({ title: "已标记今日守护", icon: "success" });
    loadData();
  } catch (e) {
    uni.showToast({ title: "标记失败", icon: "none" });
  } finally {
    submitting.value = false;
  }
}

async function pauseAlert(days) {
  if (!relationId.value) return;
  const until = new Date();
  until.setDate(until.getDate() + days);
  try {
    await updateRelation(relationId.value, { alert_paused_until: until.toISOString() });
    uni.showToast({ title: `已暂停 ${days} 天`, icon: "success" });
    loadData();
  } catch (e) {
    uni.showToast({ title: "操作失败", icon: "none" });
  }
}

function formatDate(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

function goSettings() {
  const threshold = alertThreshold.value ?? 8;
  uni.navigateTo({
    url: `/pages/elder/settings?relationId=${relationId.value}&threshold=${threshold}`,
  });
}

async function resumeAlert() {
  if (!relationId.value) return;
  try {
    await updateRelation(relationId.value, { alert_paused_until: null });
    pausedUntil.value = null;
    uni.showToast({ title: "已恢复提醒", icon: "success" });
  } catch (e) {
    uni.showToast({ title: "操作失败", icon: "none" });
  }
}
</script>

<style lang="scss" scoped>
.loading-center {
  display: flex;
  justify-content: center;
  padding-top: 300rpx;
}

.loading-dots {
  display: flex;
  gap: $sp-12;
}

.ld-dot {
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;
  background: $c-primary-soft;
  animation: ldPulse 1.2s ease-in-out infinite;
  &:nth-child(2) { animation-delay: 200ms; }
  &:nth-child(3) { animation-delay: 400ms; }
}

@keyframes ldPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

.status-content {
  padding: 0 $sp-24;
  padding-bottom: 200rpx;
}

.status-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 120rpx;
  margin-bottom: $sp-40;
}

.elder-avatar-lg {
  width: 140rpx;
  height: 140rpx;
  background: $gradient-warm;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: $shadow-glow;
  margin-bottom: $sp-20;
  border: 6rpx solid rgba(255, 255, 255, 0.8);
}

.avatar-letter {
  font-size: $fs-display;
  font-weight: $fw-bold;
  color: $c-text-inverse;
}

.elder-name {
  font-size: $fs-headline;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
}

.status-card {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-32;
  box-shadow: $shadow-md;
  margin-bottom: $sp-20;
  border: $border-subtle;
  &.safe {
    border-left: 8rpx solid $c-safe;
    background: linear-gradient(135deg, $c-safe-bg 0%, $c-surface 30%);
  }
  &.warn {
    border-left: 8rpx solid $c-warn;
    background: linear-gradient(135deg, $c-warn-bg 0%, $c-surface 30%);
  }
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: $sp-12;
  margin-bottom: $sp-8;
}

.status-dot {
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;
  &.active {
    background: $c-safe;
    box-shadow: 0 0 0 6rpx rgba($c-safe, 0.2);
  }
  &.inactive {
    background: $c-warn;
    box-shadow: 0 0 0 6rpx rgba($c-warn, 0.2);
    animation: pulse-warn 2s infinite;
  }
}

@keyframes pulse-warn {
  0%, 100% { box-shadow: 0 0 0 6rpx rgba($c-warn, 0.2); }
  50% { box-shadow: 0 0 0 10rpx rgba($c-warn, 0.1); }
}

.status-label {
  font-size: $fs-title;
  font-weight: $fw-semibold;
  color: $c-text;
}

.last-time {
  font-size: $fs-body;
  color: $c-text-sub;
  margin-left: $sp-32;
}

.checkin-area {
  margin-top: $sp-24;
}

.checkin-btn {
  text-align: center;
  padding: $sp-16;
  border-radius: $r-full;
  background: $c-safe-bg;
  color: $c-safe;
  font-size: $fs-elder-body;
  font-weight: $fw-semibold;
  transition: all $duration-normal $ease-out;
  &:active {
    transform: scale(0.97);
    background: $c-safe-soft;
    color: $c-surface;
  }
}

.pause-card {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-32;
  box-shadow: $shadow-md;
  margin-bottom: $sp-20;
  border: $border-subtle;
}

.pause-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pause-left {
  display: flex;
  align-items: center;
  gap: $sp-16;
}

.pause-icon {
  width: 40rpx;
  height: 40rpx;
  flex-shrink: 0;
}

.pause-title {
  font-size: $fs-body;
  font-weight: $fw-semibold;
  color: $c-text;
  display: block;
}

.pause-desc {
  font-size: $fs-body-sm;
  color: $c-text-hint;
  margin-top: $sp-2;
  display: block;
}

.pause-actions {
  display: flex;
  gap: $sp-12;
  margin-top: $sp-20;
}

.pause-option {
  flex: 1;
  text-align: center;
  padding: $sp-12;
  border-radius: $r-full;
  background: $c-bg-warm;
  color: $c-text-sub;
  font-size: $fs-body-sm;
  font-weight: $fw-medium;
  transition: all $duration-normal $ease-out;
  &:active {
    background: $c-primary-bg;
    color: $c-primary;
    transform: scale(0.95);
  }
}

.pause-resume-btn {
  flex: 1;
  text-align: center;
  padding: $sp-12;
  border-radius: $r-full;
  border: 2rpx solid $c-primary;
  color: $c-primary;
  font-size: $fs-body;
  font-weight: $fw-semibold;
  transition: all $duration-normal $ease-out;
  &:active {
    background: $c-primary-bg;
    transform: scale(0.97);
  }
}

.settings-entry {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-24;
  box-shadow: $shadow-md;
  margin-bottom: $sp-20;
  border: $border-subtle;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all $duration-normal $ease-out;
  &:active { transform: scale(0.98); background: $c-surface-warm; }
}

.settings-left {
  display: flex;
  align-items: center;
  gap: $sp-16;
}

.settings-icon-badge {
  width: 64rpx;
  height: 64rpx;
  border-radius: $r-md;
  background: $c-primary-bg;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.settings-icon-text {
  font-size: $fs-body;
  font-weight: $fw-bold;
  color: $c-primary;
}

.settings-title {
  font-size: $fs-body;
  font-weight: $fw-semibold;
  color: $c-text;
  display: block;
}

.settings-desc {
  font-size: $fs-body-sm;
  color: $c-text-hint;
  margin-top: $sp-2;
  display: block;
}

.settings-arrow {
  font-size: $fs-title;
  color: $c-text-hint;
}

.week-card {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-32;
  box-shadow: $shadow-md;
  border: $border-subtle;
}

.calendar-row {
  display: flex;
  justify-content: space-between;
  margin-top: $sp-8;
}

.day-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $sp-12;
}

.day-label {
  font-size: $fs-body-sm;
  color: $c-text-sub;
}

.day-ring {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  border: 3rpx solid $c-border;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all $duration-normal $ease-out;
  &.active {
    border-color: $c-safe;
    box-shadow: 0 0 0 4rpx rgba($c-safe, 0.15);
    animation: ringPop 400ms $ease-spring both;
  }
}

.day-fill {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: $c-safe;
  box-shadow: 0 2rpx 6rpx rgba($c-safe, 0.3);
  animation: fillPop 350ms $ease-spring both;
}

@keyframes ringPop {
  0% { transform: scale(0.4); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes fillPop {
  0% { transform: scale(0); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
</style>
