<template>
  <view class="page-volunteer">
    <view class="volunteer-nav" :style="{ ...navMetrics.barStyle, paddingRight: `${navMetrics.rightInset}px` }">
      <view class="volunteer-nav__back" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="volunteer-nav__title app-nav-title-center" :style="navMetrics.titleStyle">邻里帮</text>
    </view>
    <view class="volunteer-content" :style="{ paddingTop: `${navMetrics.totalHeight + 14}px` }">
      <view class="volunteer-hero">
        <text class="volunteer-hero__title">邻里帮</text>
        <text class="volunteer-hero__desc">把顺手的小事，变成社区的温暖</text>
      </view>
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
            <image class="invite-icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/neighbor-help.png" mode="aspectFit" />
          </view>
          <text class="invite-title">加入邻里帮</text>
          <text class="invite-desc">
            帮助社区里的长辈，每次探访、陪伴都能获得积分奖励。功能即将上线，敬请期待。
          </text>
          <view class="invite-features">
            <view class="invite-feature">
              <image class="invite-feature__icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/utensils.png" mode="aspectFit" />
              <text class="invite-feature__text">探访长辈</text>
            </view>
            <view class="invite-feature">
              <image class="invite-feature__icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/family.png" mode="aspectFit" />
              <text class="invite-feature__text">陪伴聊天</text>
            </view>
            <view class="invite-feature">
              <image class="invite-feature__icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/star.png" mode="aspectFit" />
              <text class="invite-feature__text">积分兑换</text>
            </view>
          </view>
          <view class="btn-register btn-register--soon" @tap="handleComingSoon">
            <text class="btn-register__text">敬请期待</text>
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
import { getNavigationBarMetrics } from "@/utils/navigation";

const volunteerStore = useVolunteerStore();
const navMetrics = getNavigationBarMetrics();
const errorLoading = ref(false);

function goBack() {
  if (getCurrentPages().length > 1) uni.navigateBack();
  else uni.switchTab({ url: "/pages/profile/index" });
}

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

function handleComingSoon() {
  uni.showToast({ title: "邻里帮即将上线，敬请期待", icon: "none" });
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
  width: 84rpx;
  height: 84rpx;
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
    width: 48rpx;
    height: 48rpx;
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

  // 功能未开放：置灰态
  &--soon {
    background: $c-bg-warm;
    box-shadow: none;

    &:active {
      transform: none;
    }

    .btn-register__text {
      color: $c-text-hint;
    }
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

<style lang="scss" scoped>
.page-volunteer {
  background:
    radial-gradient(circle at 90% 7%, rgba($c-accent,.11), transparent 24%),
    $gradient-page;
}
.volunteer-nav {
  position: fixed;
  inset: 0 0 auto 0;
  z-index: 30;
  box-sizing: content-box;
  display: flex;
  align-items: center;
  padding-left: $sp-16;
  background: rgba($c-bg,.92);
  backdrop-filter: blur(24rpx);
}
.volunteer-nav__back {
  width: 76rpx;
  height: 76rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  image { width: 34rpx; height: 34rpx; }
}
.volunteer-nav__title {
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 36rpx;
  font-weight: 800;
}
.volunteer-content { padding-left: $sp-24; padding-right: $sp-24; }
.volunteer-hero { margin: 22rpx 8rpx 30rpx; }
.volunteer-hero__title {
  display: block;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 58rpx;
  font-weight: 900;
  line-height: 1.2;
}
.volunteer-hero__desc { display: block; margin-top: 8rpx; color: $c-text-sub; font-size: 28rpx; }
.points-card {
  padding: 30rpx;
  border: 0;
  border-radius: 30rpx;
  background:
    radial-gradient(circle at 92% 10%, rgba(255,255,255,.24), transparent 28%),
    linear-gradient(135deg, #C84E3E, #E4835D);
  color: white;
  box-shadow: 0 18rpx 46rpx rgba($c-primary,.22);
}
.points-card__label,
.points-card__number,
.points-card__unit { color: white; }
.points-card__badge { background: rgba(255,255,255,.18); border: 1rpx solid rgba(255,255,255,.35); }
.points-card__badge-text,
.points-card__badge-arrow { color: white; }
.points-card__hint { color: rgba(255,255,255,.76); }
.points-card__divider { background: rgba(255,255,255,.3); }
.section {
  margin-top: 26rpx;
  padding: 26rpx;
  border: 1rpx solid rgba($c-border,.72);
  border-radius: 28rpx;
  background: rgba(255,255,255,.78);
  box-shadow: $shadow-sm;
}
.section__title {
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 36rpx;
  font-weight: 900;
}
.section__count { color: $c-text-hint; }
.task-card { border-radius: 22rpx; background: $c-bg; border: 1rpx solid $c-border-light; box-shadow: none; }
.btn-complete { border-radius: $r-full; background: $gradient-warm; }
.points-record { border-color: $c-border-light; }
.invite-card {
  padding: 42rpx 30rpx;
  border: 1rpx solid rgba($c-border,.8);
  border-radius: 34rpx;
  background: rgba(255,255,255,.84);
  box-shadow: $shadow-md;
}
.invite-title { font-family: "Songti SC", "STSong", serif; font-size: 44rpx; font-weight: 900; }
.btn-register { border-radius: $r-full; background: $gradient-warm; box-shadow: $shadow-glow; }
</style>
