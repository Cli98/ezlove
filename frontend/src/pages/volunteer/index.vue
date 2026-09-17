<template>
  <view class="page-volunteer">
    <view class="volunteer-content">
      <!-- 加载中 -->
      <view v-if="volunteerStore.profileLoading" class="loading-center">
        <view class="loading-dot-wrap">
          <view class="loading-dot" />
          <view class="loading-dot" />
          <view class="loading-dot" />
        </view>
      </view>

      <!-- 加载失败 -->
      <view v-else-if="errorLoading" class="error-state fade-in">
        <view class="error-icon-wrap">
          <text class="error-icon-text">!</text>
        </view>
        <text class="error-title">加载失败</text>
        <text class="error-desc">网络不太好，请稍后再试</text>
        <view class="error-retry-btn" @tap="retryLoad">
          <text class="error-retry-btn-text">重新加载</text>
        </view>
      </view>

      <!-- 未注册：邀请卡片 -->
      <view v-else-if="!volunteerStore.profile" class="invite-section fade-in">
        <view class="invite-card">
          <view class="invite-icon-wrap">
            <text class="invite-icon">&#x1F91D;</text>
          </view>
          <text class="invite-title">加入邻里帮</text>
          <text class="invite-desc">
            帮助社区里的长辈，每次探访、陪伴都能获得积分奖励。用温暖换温暖，让社区更有爱。
          </text>
          <view class="invite-features">
            <view class="invite-feature">
              <text class="invite-feature__icon">&#x2615;</text>
              <text class="invite-feature__text">探访长辈</text>
            </view>
            <view class="invite-feature">
              <text class="invite-feature__icon">&#x1F3B5;</text>
              <text class="invite-feature__text">陪伴聊天</text>
            </view>
            <view class="invite-feature">
              <text class="invite-feature__icon">&#x1F381;</text>
              <text class="invite-feature__text">积分兑换</text>
            </view>
          </view>
          <view class="btn-register" @tap="handleRegister">
            <text class="btn-register__text">加入邻里帮</text>
          </view>
        </view>
      </view>

      <!-- 已注册：主面板 -->
      <view v-else>
        <!-- 积分卡片 -->
        <view class="points-card fade-in">
          <view class="points-card__header">
            <text class="points-card__label">我的积分</text>
            <view class="points-card__badge" @tap="goTasks">
              <text class="points-card__badge-text">去接任务</text>
              <text class="points-card__badge-arrow">&#x203A;</text>
            </view>
          </view>
          <view class="points-card__body">
            <view class="points-card__total">
              <text class="points-card__number">{{ volunteerStore.profile?.total_points || 0 }}</text>
              <text class="points-card__unit">总积分</text>
            </view>
            <view class="points-card__divider"></view>
            <view class="points-card__available">
              <text class="points-card__number points-card__number--sub">{{ volunteerStore.profile?.available_points || 0 }}</text>
              <text class="points-card__unit">可用积分</text>
            </view>
          </view>
        </view>

        <!-- 我的任务 -->
        <view class="section fade-in stagger-1">
          <view class="section__header">
            <text class="section__title">我的任务</text>
            <text class="section__count">{{ myTasks.length }}项</text>
          </view>

          <view v-if="myTasks.length === 0" class="empty-hint">
            <text class="empty-hint__text">暂无进行中的任务，去看看有什么可以帮忙的吧</text>
          </view>

          <view v-else class="task-list">
            <view
              v-for="task in myTasks"
              :key="task.id"
              class="task-card"
            >
              <view class="task-card__left">
                <view class="task-card__type-tag" :class="'task-card__type-tag--' + task.task_type">
                  <text class="task-card__type-text">{{ taskTypeLabel(task.task_type) }}</text>
                </view>
                <view class="task-card__info">
                  <text class="task-card__title">{{ task.title }}</text>
                  <text class="task-card__elder">{{ task.target_elder_name || '待定' }}</text>
                </view>
              </view>
              <view class="task-card__right">
                <text class="task-card__points">+{{ task.point_value }}</text>
                <view class="btn-complete" @tap="handleComplete(task)">
                  <text class="btn-complete__text">完成</text>
                </view>
              </view>
            </view>
          </view>
        </view>

        <!-- 积分记录 -->
        <view class="section fade-in stagger-2">
          <view class="section__header">
            <text class="section__title">积分记录</text>
          </view>

          <view v-if="volunteerStore.points.length === 0" class="empty-hint">
            <text class="empty-hint__text">完成任务即可获得积分</text>
          </view>

          <view v-else class="points-list">
            <view
              v-for="record in volunteerStore.points"
              :key="record.id"
              class="points-record"
            >
              <view class="points-record__left">
                <text class="points-record__desc">{{ record.description }}</text>
                <text class="points-record__time">{{ formatTime(record.created_at) }}</text>
              </view>
              <text
                class="points-record__amount"
                :class="record.amount > 0 ? 'points-record__amount--plus' : 'points-record__amount--minus'"
              >
                {{ record.amount > 0 ? '+' : '' }}{{ record.amount }}
              </text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onShow, onPullDownRefresh } from "@dcloudio/uni-app";
import { useVolunteerStore } from "@/stores/volunteer";

const volunteerStore = useVolunteerStore();
const errorLoading = ref(false);

const myTasks = computed(() => {
  return volunteerStore.tasks.filter((t) => t.status === "accepted");
});

function taskTypeLabel(type) {
  const map = { visit: "探访", accompany: "陪伴", check_in: "签到", errand: "代办" };
  return map[type] || type;
}

function formatTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  const month = (d.getMonth() + 1).toString().padStart(2, "0");
  const day = d.getDate().toString().padStart(2, "0");
  const h = d.getHours().toString().padStart(2, "0");
  const m = d.getMinutes().toString().padStart(2, "0");
  return `${month}-${day} ${h}:${m}`;
}

async function handleRegister() {
  try {
    await volunteerStore.register();
    uni.showToast({ title: "欢迎加入邻里帮", icon: "none" });
  } catch {
    uni.showToast({ title: "注册失败，请稍后再试", icon: "none" });
  }
}

async function handleComplete(task) {
  uni.showModal({
    title: "确认完成",
    content: `确定已完成「${task.title}」吗？`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await volunteerStore.complete(task.id, {});
          uni.showToast({ title: "任务完成，积分已到账", icon: "none" });
          volunteerStore.loadTasks();
          volunteerStore.loadPoints();
          volunteerStore.loadProfile();
        } catch {
          uni.showToast({ title: "操作失败，请稍后再试", icon: "none" });
        }
      }
    },
  });
}

function goTasks() {
  uni.navigateTo({ url: "/pages/volunteer/tasks" });
}

async function retryLoad() {
  errorLoading.value = false;
  try {
    await volunteerStore.loadProfile();
    volunteerStore.loadTasks();
    volunteerStore.loadPoints();
  } catch {
    errorLoading.value = true;
  }
}

onShow(async () => {
  try {
    await volunteerStore.loadProfile();
    errorLoading.value = false;
    volunteerStore.loadTasks();
    volunteerStore.loadPoints();
  } catch {
    errorLoading.value = true;
  }
});

onPullDownRefresh(async () => {
  try {
    await Promise.all([
      volunteerStore.loadProfile(),
      volunteerStore.loadTasks(),
      volunteerStore.loadPoints(),
    ]);
    errorLoading.value = false;
  } catch {
    errorLoading.value = true;
  } finally {
    uni.stopPullDownRefresh();
  }
});
</script>

<style lang="scss" scoped>
.page-volunteer {
  min-height: 100vh;
  background-color: $c-bg;
}

.volunteer-content {
  padding: $sp-24;
  padding-bottom: 200rpx;
}

// ── 加载 ──
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
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;
  background: $c-primary;
  animation: ldPulse 1.2s ease-in-out infinite;
  &:nth-child(2) { animation-delay: 200ms; }
  &:nth-child(3) { animation-delay: 400ms; }
}

@keyframes ldPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

// ── 加载失败 ──
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.error-icon-wrap {
  width: 96rpx;
  height: 96rpx;
  background: $c-warn-bg;
  border-radius: $r-full;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $sp-24;
}

.error-icon-text {
  font-size: 48rpx;
  font-weight: $fw-bold;
  color: $c-warn;
}

.error-title {
  font-size: $fs-headline;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
}

.error-desc {
  font-size: $fs-body;
  color: $c-text-sub;
  margin-top: $sp-8;
  display: block;
}

.error-retry-btn {
  margin-top: $sp-32;
  padding: $sp-16 $sp-48;
  background: $c-primary;
  border-radius: $r-full;
  box-shadow: $shadow-md;
  transition: transform $duration-normal $ease-out;

  &:active {
    transform: scale(0.95);
  }
}

.error-retry-btn-text {
  font-size: $fs-body;
  font-weight: $fw-bold;
  color: $c-text-inverse;
}

// ── 邀请卡片 ──
.invite-card {
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-48 $sp-32;
  box-shadow: $shadow-md;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: $sp-32;
}

.invite-icon-wrap {
  width: 160rpx;
  height: 160rpx;
  background: $c-primary-bg;
  border-radius: $r-full;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $sp-24;
}

.invite-icon {
  font-size: 80rpx;
  line-height: 1;
}

.invite-title {
  font-size: $fs-headline;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
  margin-bottom: $sp-12;
}

.invite-desc {
  font-size: $fs-title;
  color: $c-text-sub;
  text-align: center;
  line-height: $lh-relaxed;
  display: block;
  margin-bottom: $sp-32;
}

.invite-features {
  display: flex;
  gap: $sp-32;
  margin-bottom: $sp-40;
}

.invite-feature {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $sp-8;

  &__icon {
    font-size: 48rpx;
    line-height: 1;
  }

  &__text {
    font-size: $fs-body;
    color: $c-text-sub;
    font-weight: $fw-medium;
  }
}

.btn-register {
  width: 100%;
  padding: $sp-20 0;
  background: $gradient-warm;
  border-radius: $r-full;
  text-align: center;
  box-shadow: $shadow-glow;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.97);
    box-shadow: $shadow-sm;
  }

  &__text {
    font-size: $fs-title;
    font-weight: $fw-bold;
    color: $c-text-inverse;
  }
}

// ── 积分卡片 ──
.points-card {
  background: $gradient-warm;
  border-radius: $r-xl;
  padding: $sp-24 $sp-24;
  box-shadow: $shadow-glow;
  margin-bottom: $sp-24;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $sp-20;
  }

  &__label {
    font-size: $fs-body;
    color: rgba(255, 255, 255, 0.85);
    font-weight: $fw-medium;
  }

  &__badge {
    display: flex;
    align-items: center;
    gap: $sp-4;
    padding: $sp-6 $sp-16;
    background: rgba(255, 255, 255, 0.2);
    border-radius: $r-full;
    transition: all $duration-normal $ease-out;

    &:active {
      background: rgba(255, 255, 255, 0.3);
    }
  }

  &__badge-text {
    font-size: $fs-body-sm;
    color: $c-text-inverse;
    font-weight: $fw-medium;
  }

  &__badge-arrow {
    font-size: $fs-body;
    color: $c-text-inverse;
  }

  &__body {
    display: flex;
    align-items: center;
    gap: $sp-24;
  }

  &__total,
  &__available {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
  }

  &__divider {
    width: 2rpx;
    height: 80rpx;
    background: rgba(255, 255, 255, 0.3);
  }

  &__number {
    font-size: $fs-display;
    font-weight: $fw-bold;
    color: $c-text-inverse;
    display: block;
    line-height: 1.2;

    &--sub {
      font-size: $fs-headline;
    }
  }

  &__unit {
    font-size: $fs-body-sm;
    color: rgba(255, 255, 255, 0.75);
    margin-top: $sp-4;
  }
}

// ── 区块标题 ──
.section {
  margin-bottom: $sp-24;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $sp-16;
  }

  &__title {
    font-size: $fs-title;
    font-weight: $fw-bold;
    color: $c-text;
  }

  &__count {
    font-size: $fs-body-sm;
    color: $c-text-hint;
  }
}

// ── 空提示 ──
.empty-hint {
  background: $c-surface;
  border-radius: $r-lg;
  padding: $sp-32 $sp-24;
  text-align: center;

  &__text {
    font-size: $fs-body;
    color: $c-text-hint;
    line-height: $lh-relaxed;
  }
}

// ── 任务卡片 ──
.task-list {
  display: flex;
  flex-direction: column;
  gap: $sp-12;
}

.task-card {
  background: $c-surface;
  border-radius: $r-lg;
  padding: $sp-20;
  box-shadow: $shadow-sm;
  display: flex;
  align-items: center;
  justify-content: space-between;

  &__left {
    display: flex;
    align-items: center;
    gap: $sp-12;
    flex: 1;
    min-width: 0;
  }

  &__type-tag {
    padding: $sp-6 $sp-12;
    border-radius: $r-sm;
    flex-shrink: 0;

    &--visit {
      background: $c-primary-bg;
    }

    &--accompany {
      background: $c-accent-bg;
    }

    &--check_in {
      background: $c-safe-bg;
    }

    &--errand {
      background: $c-warn-bg;
    }
  }

  &__type-text {
    font-size: $fs-body-sm;
    font-weight: $fw-medium;
    color: $c-text;
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__title {
    font-size: $fs-body;
    font-weight: $fw-semibold;
    color: $c-text;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__elder {
    font-size: $fs-body-sm;
    color: $c-text-sub;
    display: block;
    margin-top: $sp-2;
  }

  &__right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: $sp-8;
    flex-shrink: 0;
    margin-left: $sp-12;
  }

  &__points {
    font-size: $fs-body;
    font-weight: $fw-bold;
    color: $c-accent;
  }
}

.btn-complete {
  padding: $sp-6 $sp-16;
  background: $c-safe;
  border-radius: $r-full;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.95);
    background: darken($c-safe, 5%);
  }

  &__text {
    font-size: $fs-body-sm;
    color: $c-text-inverse;
    font-weight: $fw-medium;
  }
}

// ── 积分记录 ──
.points-list {
  background: $c-surface;
  border-radius: $r-lg;
  overflow: hidden;
  box-shadow: $shadow-sm;
}

.points-record {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $sp-16 $sp-20;
  border-bottom: $border-subtle;

  &:last-child {
    border-bottom: none;
  }

  &__left {
    flex: 1;
    min-width: 0;
  }

  &__desc {
    font-size: $fs-body;
    color: $c-text;
    display: block;
    font-weight: $fw-medium;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  &__time {
    font-size: $fs-body-sm;
    color: $c-text-hint;
    display: block;
    margin-top: $sp-4;
  }

  &__amount {
    font-size: $fs-title;
    font-weight: $fw-bold;
    flex-shrink: 0;
    margin-left: $sp-16;

    &--plus {
      color: $c-safe;
    }

    &--minus {
      color: $c-warn;
    }
  }
}
</style>
