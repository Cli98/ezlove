<template>
  <view class="page-tasks">
    <view class="tasks-nav" :style="{ ...navMetrics.barStyle, paddingRight: `${navMetrics.rightInset}px` }">
      <view class="tasks-nav__back" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="tasks-nav__title app-nav-title-center" :style="navMetrics.titleStyle">邻里任务</text>
    </view>
    <view class="tasks-content" :style="{ paddingTop: `${navMetrics.totalHeight + 14}px` }">
      <view class="tasks-hero">
        <text class="tasks-hero__title">附近可以帮上的忙</text>
        <text class="tasks-hero__desc">一份帮忙，一份温暖，让邻里更亲近</text>
      </view>
      <!-- 加载中 -->
      <view v-if="volunteerStore.loading" class="loading-center fade-in">
        <view class="loading-dot-wrap">
          <view class="loading-dot" />
          <view class="loading-dot" />
          <view class="loading-dot" />
        </view>
      </view>

      <!-- 空状态 -->
      <view v-else-if="availableTasks.length === 0" class="empty-state fade-in">
        <view class="empty-icon-wrap">
          <image class="empty-icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/neighbor-help.png" mode="aspectFit" />
        </view>
        <text class="empty-title">暂时没有可接任务</text>
        <text class="empty-desc">社区会不定期发布任务，请稍后再来看看</text>
      </view>

      <!-- 任务列表 -->
      <view v-else class="task-list">
        <view
          v-for="(task, index) in availableTasks"
          :key="task.id"
          class="task-card fade-in"
          :class="'stagger-' + Math.min(index + 1, 4)"
        >
          <view class="task-card__top">
            <view class="task-card__type-tag" :class="'task-card__type-tag--' + task.task_type">
              <text class="task-card__type-text">{{ taskTypeLabel(task.task_type) }}</text>
            </view>
            <view class="task-card__points-badge">
              <text class="task-card__points-text">+{{ task.point_value }}积分</text>
            </view>
          </view>

          <text class="task-card__title">{{ task.title }}</text>

          <view v-if="task.target_elder_name" class="task-card__elder-row">
            <text class="task-card__elder-label">服务对象：</text>
            <text class="task-card__elder-name">{{ task.target_elder_name }}</text>
          </view>

          <view v-if="task.notes" class="task-card__desc-row">
            <text class="task-card__desc">{{ task.notes }}</text>
          </view>

          <view class="task-card__bottom">
            <text v-if="task.deadline" class="task-card__deadline">截止 {{ formatDate(task.deadline) }}</text>
            <view v-else class="task-card__spacer"></view>
            <view class="btn-accept" @tap="handleAccept(task)">
              <text class="btn-accept__text">接受任务</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";
import { onShow, onPullDownRefresh } from "@dcloudio/uni-app";
import { useVolunteerStore } from "@/stores/volunteer";
import { getNavigationBarMetrics } from "@/utils/navigation";

const volunteerStore = useVolunteerStore();
const navMetrics = getNavigationBarMetrics();

function goBack() {
  uni.navigateBack();
}

const availableTasks = computed(() => {
  return volunteerStore.tasks.filter((t) => t.status === "pending");
});

function taskTypeLabel(type) {
  const map = { visit: "探访", accompany: "陪伴", check_in: "签到", errand: "代办" };
  return map[type] || type;
}

function formatDate(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  const month = (d.getMonth() + 1).toString().padStart(2, "0");
  const day = d.getDate().toString().padStart(2, "0");
  return `${month}月${day}日`;
}

async function handleAccept(task) {
  uni.showModal({
    title: "接受任务",
    content: `确定接受「${task.title}」吗？`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await volunteerStore.accept(task.id);
          uni.showToast({ title: "任务已接受", icon: "none" });
          volunteerStore.loadTasks();
        } catch {
          uni.showToast({ title: "接受失败，请稍后再试", icon: "none" });
        }
      }
    },
  });
}

onShow(() => {
  volunteerStore.loadTasks();
});

onPullDownRefresh(async () => {
  try {
    await volunteerStore.loadTasks();
  } finally {
    uni.stopPullDownRefresh();
  }
});
</script>

<style lang="scss" scoped>
.page-tasks {
  min-height: 100vh;
  background-color: $c-bg;
}

.tasks-content {
  padding: $sp-24;
  padding-bottom: 200rpx;
}

// ── 加载中 ──
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
  animation: dotPulse 1.2s ease-in-out infinite;
  &:nth-child(2) { animation-delay: 200ms; }
  &:nth-child(3) { animation-delay: 400ms; }
}

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

// ── 空状态 ──
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.empty-icon-wrap {
  width: 160rpx;
  height: 160rpx;
  background: $c-primary-bg;
  border-radius: $r-full;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $sp-24;
}

.empty-icon {
  width: 72rpx;
  height: 72rpx;
}

.empty-title {
  font-size: $fs-title;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
  margin-bottom: $sp-8;
}

.empty-desc {
  font-size: $fs-body;
  color: $c-text-sub;
  display: block;
}

// ── 任务列表 ──
.task-list {
  display: flex;
  flex-direction: column;
  gap: $sp-20;
}

.task-card {
  background: $c-surface;
  border-radius: $r-lg;
  padding: $sp-24;
  box-shadow: $shadow-sm;
  border: $border-subtle;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.99);
    box-shadow: $shadow-xs;
  }

  &__top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $sp-12;
  }

  &__type-tag {
    padding: $sp-6 $sp-16;
    border-radius: $r-full;

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
    font-weight: $fw-semibold;
    color: $c-text;
  }

  &__points-badge {
    padding: $sp-4 $sp-12;
    background: $c-accent-bg;
    border-radius: $r-full;
  }

  &__points-text {
    font-size: $fs-body-sm;
    font-weight: $fw-bold;
    color: $c-accent;
  }

  &__title {
    font-size: $fs-title;
    font-weight: $fw-bold;
    color: $c-text;
    display: block;
    margin-bottom: $sp-8;
    line-height: $lh-tight;
  }

  &__elder-row {
    display: flex;
    align-items: center;
    margin-bottom: $sp-8;
  }

  &__elder-label {
    font-size: $fs-body;
    color: $c-text-hint;
  }

  &__elder-name {
    font-size: $fs-body;
    color: $c-text;
    font-weight: $fw-medium;
  }

  &__desc-row {
    margin-bottom: $sp-12;
  }

  &__desc {
    font-size: $fs-body-sm;
    color: $c-text-sub;
    line-height: $lh-relaxed;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: $sp-16;
    padding-top: $sp-16;
    border-top: $border-subtle;
  }

  &__deadline {
    font-size: $fs-body-sm;
    color: $c-text-hint;
  }

  &__spacer {
    flex: 1;
  }
}

.btn-accept {
  padding: $sp-10 $sp-24;
  background: $c-primary;
  border-radius: $r-full;
  box-shadow: $shadow-sm;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.95);
    background: $c-primary-hover;
  }

  &__text {
    font-size: $fs-body;
    font-weight: $fw-bold;
    color: $c-text-inverse;
  }
}
</style>

<style lang="scss" scoped>
.page-tasks {
  min-height: 100vh;
  background:
    radial-gradient(circle at 92% 8%, rgba($c-accent,.11), transparent 24%),
    $gradient-page;
}
.tasks-nav {
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
.tasks-nav__back {
  width: 76rpx;
  height: 76rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  image { width: 34rpx; height: 34rpx; }
}
.tasks-nav__title {
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 36rpx;
  font-weight: 800;
}
.tasks-content { padding-left: $sp-24; padding-right: $sp-24; }
.tasks-hero { margin: 22rpx 8rpx 34rpx; }
.tasks-hero__title {
  display: block;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 52rpx;
  font-weight: 900;
  line-height: 1.2;
}
.tasks-hero__desc { display: block; margin-top: 10rpx; color: $c-text-sub; font-size: 27rpx; }
.task-list { gap: 18rpx; }
.task-card {
  padding: 26rpx;
  border: 1rpx solid rgba($c-border,.74);
  border-radius: 26rpx;
  background: rgba(255,255,255,.82);
  box-shadow: $shadow-sm;
}
.task-card__title { font-family: "Songti SC", "STSong", serif; font-size: 34rpx; font-weight: 800; }
.task-card__desc-row { border-radius: 16rpx; background: $c-bg-warm; }
.btn-accept { min-width: 168rpx; border-radius: $r-full; background: $gradient-warm; box-shadow: 0 8rpx 20rpx rgba($c-primary,.18); }
.empty-state { padding-top: 90rpx; }
</style>
