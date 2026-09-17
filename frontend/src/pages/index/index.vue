<template>
  <view class="page-home">
    <!-- 顶部导航栏 -->
    <view class="top-bar">
      <view class="top-bar__left">
        <view class="top-bar__avatar">
          <text class="top-bar__avatar-text">{{ (userStore.profile?.nickname || '我')[0] }}</text>
        </view>
        <text class="top-bar__greeting">你好，{{ userStore.profile?.nickname || '家人' }}</text>
      </view>
      <view class="top-bar__bell" @tap="goAlerts">
        <image class="top-bar__bell-icon" src="/static/icons/notification.svg" mode="aspectFit" />
        <view v-if="alertStore.unresolvedCount > 0" class="top-bar__badge">
          <text class="top-bar__badge-text">{{ alertStore.unresolvedCount > 99 ? '99+' : alertStore.unresolvedCount }}</text>
        </view>
      </view>
    </view>

    <view class="home-content">
      <!-- 大字问候区域 -->
      <view class="greeting-section fade-in">
        <text class="greeting-title" :class="{ 'greeting-title--elder': userStore.isElder }">{{ greeting }}</text>
        <view class="greeting-sub-row">
          <text class="greeting-sub" :class="{ 'greeting-sub--elder': userStore.isElder }">
            {{ userStore.isFamily ? '今日牵挂状态' : '看看孩子们的分享' }}
          </text>
          <view class="pulse-dot"></view>
        </view>
      </view>

      <!-- 子女端：绑定家人列表 -->
      <view v-if="userStore.isFamily" class="elder-section">
        <view v-if="relationStore.loading" class="loading-center fade-in">
          <view class="loading-dot-wrap">
            <view class="loading-dot" />
            <view class="loading-dot" />
            <view class="loading-dot" />
          </view>
        </view>
        <view v-else-if="relationStore.relations.length === 0" class="empty-state fade-in stagger-1">
          <view class="empty-icon-wrap">
            <image class="empty-icon" src="/static/icons/link.svg" mode="aspectFit" />
          </view>
          <text class="empty-title">思念需要一个出口</text>
          <text class="empty-desc">邀请家人加入，让关心不再只放在心里</text>
          <view class="btn-primary empty-btn" @tap="goInvite">邀请家人</view>
        </view>

        <view v-else class="elder-list">
          <view
            v-for="(elder, index) in relationStore.relations"
            :key="elder.id"
            class="elder-card fade-in"
            :class="'stagger-' + Math.min(index + 1, 4)"
            @tap="goElderStatus(elder)"
          >
            <view class="elder-card__left">
              <view
                class="elder-card__avatar"
                :style="{ backgroundColor: getAvatarColor(index).bg }"
              >
                <text class="elder-card__avatar-text" :style="{ color: getAvatarColor(index).text }">
                  {{ (elder.elder_name || elder.relation_label || '家')[0] }}
                </text>
              </view>
              <view class="elder-card__info">
                <view class="elder-card__name-row">
                  <text class="elder-card__name">{{ elder.elder_name || elder.relation_label || '家人' }}</text>
                  <view
                    class="elder-card__badge"
                    :class="elder.today_read ? 'elder-card__badge--read' : 'elder-card__badge--unread'"
                  >
                    <text>{{ elder.today_read ? '今日已读' : '今日未读' }}</text>
                  </view>
                </view>
                <text class="elder-card__time">{{ elder.last_active_text || '暂无活跃记录' }}</text>
              </view>
            </view>
            <image class="elder-card__chevron" src="/static/icons/chevron-right.svg" mode="aspectFit" />
          </view>
        </view>
      </view>

      <!-- 老人端：查看子女发来的牵挂 -->
      <view v-else class="elder-home">
        <!-- 报平安按钮 -->
        <view class="checkin-section fade-in stagger-1">
          <view
            class="checkin-btn"
            :class="[checkedInToday ? 'checkin-btn--done' : 'checkin-btn--active', { 'checkin-ripple': showRipple }]"
            @tap="handleCheckIn"
          >
            <image
              class="checkin-btn__icon"
              :src="checkedInToday ? '/static/icons/checkmark.svg' : '/static/icons/sun.svg'"
              mode="aspectFit"
            />
            <view class="checkin-btn__text-wrap">
              <text class="checkin-btn__title">{{ checkedInToday ? '今天已报平安' : '我今天很好' }}</text>
              <text class="checkin-btn__sub">{{ checkedInToday ? checkinTimeText : '点一下，让关心你的人放心' }}</text>
            </view>
          </view>
        </view>

        <!-- 今日菜单 -->
        <view v-if="todayMenuDishes.length" class="menu-section fade-in stagger-2">
          <view class="menu-card">
            <view class="menu-card__header">
              <image class="menu-card__icon" src="/static/icons/utensils.svg" mode="aspectFit" />
              <text class="menu-card__title">今日菜单</text>
              <text class="menu-card__meal">{{ menuMealLabel }}</text>
            </view>
            <view class="menu-card__dishes">
              <view v-for="(dish, i) in todayMenuDishes" :key="i" class="menu-dish">
                <view
                  class="menu-dish__dot"
                  :class="dish.category === '荤菜' ? 'menu-dish__dot--meat' : 'menu-dish__dot--veg'"
                />
                <view class="menu-dish__info">
                  <text class="menu-dish__name">{{ dish.name }}</text>
                  <text class="menu-dish__desc">{{ dish.description }}</text>
                </view>
              </view>
            </view>
            <view v-if="todayMenuData.soup" class="menu-card__extra">
              <text class="menu-card__extra-label">汤品</text>
              <text class="menu-card__extra-text">{{ todayMenuData.soup }}</text>
            </view>
            <view v-if="todayMenuData.staple" class="menu-card__extra">
              <text class="menu-card__extra-label">主食</text>
              <text class="menu-card__extra-text">{{ todayMenuData.staple }}</text>
            </view>
          </view>
        </view>

        <!-- 邻里帮入口 -->
        <view class="volunteer-entry fade-in stagger-2" @tap="goVolunteer">
          <view class="volunteer-entry__left">
            <image class="volunteer-entry__icon" src="/static/icons/handshake.svg" mode="aspectFit" />
            <view class="volunteer-entry__info">
              <text class="volunteer-entry__title">邻里帮</text>
              <text class="volunteer-entry__desc">帮助邻居，赚取积分</text>
            </view>
          </view>
          <text class="volunteer-entry__arrow">›</text>
        </view>

        <view v-if="momentStore.loading" class="loading-center fade-in">
          <view class="loading-dot-wrap">
            <view class="loading-dot" />
            <view class="loading-dot" />
            <view class="loading-dot" />
          </view>
        </view>

        <view v-else-if="momentStore.moments.length === 0" class="empty-state-elder fade-in stagger-1">
          <view class="empty-icon-wrap-elder">
            <image class="empty-icon-elder" src="/static/icons/sun.svg" mode="aspectFit" />
          </view>
          <text class="empty-title-elder">今天天气真好呀</text>
          <text class="empty-desc-elder">孩子们正在准备给您的惊喜呢，稍等一会儿~</text>
        </view>

        <view v-else class="elder-moment-list">
          <view
            v-for="(m, index) in momentStore.moments"
            :key="m.id"
            class="elder-moment-card fade-in"
            :class="'stagger-' + Math.min(index + 1, 4)"
            @tap="goViewDetail(m)"
          >
            <view class="elder-moment-card__left">
              <view class="elder-moment-card__avatar">
                <text class="elder-moment-card__avatar-text">{{ (m.sender_name || '家')[0] }}</text>
              </view>
              <view class="elder-moment-card__info">
                <view class="elder-moment-card__name-row">
                  <text class="elder-moment-card__name">{{ m.sender_name || '家人' }}</text>
                  <view class="elder-moment-card__badge">
                    <text>发来牵挂</text>
                  </view>
                </view>
                <text class="elder-moment-card__time">{{ m.created_at_text || '' }}</text>
              </view>
            </view>
            <image class="elder-moment-card__chevron" src="/static/icons/chevron-right.svg" mode="aspectFit" />
          </view>
        </view>
      </view>
    </view>

    <!-- 底部装饰线 -->
    <view v-if="userStore.isFamily && relationStore.relations.length > 0" class="deco-line-wrap fade-in stagger-4">
      <view class="deco-line"></view>
    </view>

    <!-- FAB 浮动按钮 -->
    <view v-if="userStore.isFamily && relationStore.relations.length > 0" class="fab fade-in stagger-3" @tap="goSend">
      <image class="fab__icon" src="/static/icons/heart-send.svg" mode="aspectFit" />
      <text class="fab__text">发送牵挂</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onShow, onPullDownRefresh } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";
import { useRelationStore } from "@/stores/relation";
import { useMomentStore } from "@/stores/moment";
import { useAlertStore } from "@/stores/alert";
import { selfCheckIn, getTodayCheckIn } from "@/api/user";
import { getTodayMenu } from "@/api/canteen";

const AVATAR_COLORS = [
  { bg: '#FBEAE8', text: '#C44D3E' },
  { bg: '#FBF3E8', text: '#C4943E' },
  { bg: '#E8F3E7', text: '#5E8F5A' },
];

function getAvatarColor(index) {
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}

const userStore = useUserStore();
const relationStore = useRelationStore();
const momentStore = useMomentStore();
const alertStore = useAlertStore();

const checkedInToday = ref(false);
const checkinTimeText = ref("");
const showRipple = ref(false);
const checkingIn = ref(false);
const todayMenus = ref([]);

const todayMenuData = computed(() => todayMenus.value[0]?.dishes || {});
const todayMenuDishes = computed(() => todayMenuData.value.items || []);
const menuMealLabel = computed(() => {
  const type = todayMenus.value[0]?.meal_type;
  return type === "dinner" ? "晚餐" : "午餐";
});

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
});


function formatCheckinTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  const h = d.getHours().toString().padStart(2, "0");
  const m = d.getMinutes().toString().padStart(2, "0");
  return `${h}:${m} 已报平安`;
}

async function loadCheckinStatus() {
  try {
    const res = await getTodayCheckIn();
    checkedInToday.value = res.checked_in;
    checkinTimeText.value = formatCheckinTime(res.checked_in_at);
  } catch (e) {
    console.warn('报平安状态加载失败', e);
  }
}

async function handleCheckIn() {
  if (checkedInToday.value || checkingIn.value) return;
  checkingIn.value = true;
  try {
    const res = await selfCheckIn();
    showRipple.value = true;
    setTimeout(() => { showRipple.value = false; }, 800);
    checkedInToday.value = true;
    checkinTimeText.value = formatCheckinTime(res.checked_in_at);
    uni.showToast({ title: "已报平安，家人们安心了", icon: "none" });
  } catch (e) {
    uni.showToast({ title: "报平安失败，请稍后再试", icon: "none" });
  } finally {
    checkingIn.value = false;
  }
}

onShow(() => {
  alertStore.loadAlerts();
  if (userStore.isFamily) {
    relationStore.loadRelations();
  } else {
    momentStore.loadMoments();
    loadCheckinStatus();
    loadTodayMenu();
  }
});

onPullDownRefresh(async () => {
  try {
    alertStore.loadAlerts();
    if (userStore.isFamily) {
      await relationStore.loadRelations();
    } else {
      await momentStore.loadMoments();
      await loadCheckinStatus();
      await loadTodayMenu();
    }
  } finally {
    uni.stopPullDownRefresh();
  }
});

async function loadTodayMenu() {
  try {
    const res = await getTodayMenu();
    todayMenus.value = res.menus || [];
  } catch (e) {
    console.warn('今日菜单加载失败', e);
  }
}

function goSend() {
  uni.navigateTo({ url: "/pages/send/index" });
}

function goElderStatus(elder) {
  uni.navigateTo({ url: `/pages/elder/status?id=${elder.elder_user_id}` });
}

function goInvite() {
  uni.navigateTo({ url: "/pages/bind/invite" });
}

function goViewDetail(m) {
  uni.navigateTo({ url: `/pages/view/detail?id=${m.id}` });
}

function goAlerts() {
  uni.switchTab({ url: "/pages/alerts/index" });
}

function goVolunteer() {
  uni.navigateTo({ url: "/pages/volunteer/index" });
}
</script>

<style lang="scss" scoped>
// ── 页面背景 ──
.page-home {
  min-height: 100vh;
  background: #FBF7F2;
  position: relative;
}

// ── 顶部导航栏 ──
.top-bar {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 50;
  background: #FBF7F2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32rpx 48rpx;
  padding-top: calc(var(--status-bar-height, 50rpx) + 32rpx);
  box-sizing: border-box;

  &__left {
    display: flex;
    align-items: center;
    gap: 24rpx;
  }

  &__avatar {
    width: 80rpx;
    height: 80rpx;
    border-radius: $r-full;
    background: #EFE9E1;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    flex-shrink: 0;
  }

  &__avatar-text {
    font-size: $fs-body;
    font-weight: $fw-bold;
    color: #C75C3A;
  }

  &__greeting {
    font-size: $fs-body;
    font-weight: $fw-medium;
    color: #C75C3A;
  }

  &__bell {
    width: 80rpx;
    height: 80rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  &__bell-icon {
    width: 48rpx;
    height: 48rpx;
  }

  &__badge {
    position: absolute;
    top: 0;
    right: 0;
    min-width: 32rpx;
    height: 32rpx;
    background: #C44D3E;
    border-radius: $r-full;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 8rpx;
    border: 3rpx solid #FFFFFF;
  }

  &__badge-text {
    font-size: 20rpx;
    color: #FFFFFF;
    font-weight: $fw-bold;
    line-height: 1;
  }
}

// ── 主内容区 ──
.home-content {
  padding-top: calc(var(--status-bar-height, 50rpx) + 160rpx);
  padding-left: 48rpx;
  padding-right: 48rpx;
  padding-bottom: 260rpx;
}

// ── 问候区域 ──
.greeting-section {
  margin-bottom: 80rpx;
  padding: $sp-8 0 $sp-16;
}

.greeting-title {
  font-size: 72rpx;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
  margin-bottom: $sp-8;
  letter-spacing: -1rpx;

  &--elder {
    font-size: $fs-elder-headline;
  }
}

.greeting-sub-row {
  display: flex;
  align-items: center;
  gap: $sp-8;
}

.greeting-sub {
  font-size: 32rpx;
  color: $c-text-sub;

  &--elder {
    font-size: $fs-elder-body;
  }
}

.pulse-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: $r-full;
  background-color: #C75C3A;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}


// ── 子女端：空状态 ──
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: $sp-64 $sp-24;
  background: $c-surface;
  border-radius: $r-lg;
  box-shadow: $shadow-sm;
}

.empty-icon-wrap {
  width: 120rpx;
  height: 120rpx;
  background: $c-primary-bg;
  border-radius: $r-full;
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

// ── 子女端：长辈卡片列表 ──
.elder-list {
  display: flex;
  flex-direction: column;
  gap: $sp-12;
}

.elder-card {
  background: #FFFFFF;
  border-radius: 32rpx;
  padding: 40rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: transform $duration-normal $ease-out;

  &:active {
    transform: scale(0.98);
  }

  &__left {
    display: flex;
    align-items: center;
    gap: 32rpx;
    flex: 1;
    min-width: 0;
  }

  &__avatar {
    width: 112rpx;
    height: 112rpx;
    border-radius: $r-full;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  &__avatar-text {
    font-size: 42rpx;
    font-weight: $fw-bold;
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name-row {
    display: flex;
    align-items: center;
    gap: $sp-8;
    margin-bottom: $sp-4;
  }

  &__name {
    font-size: 36rpx;
    font-weight: $fw-bold;
    color: $c-text;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200rpx;
  }

  &__badge {
    padding: 4rpx 16rpx;
    border-radius: $r-full;
    font-size: 24rpx;
    font-weight: $fw-medium;

    &--unread {
      background-color: #FBEAE8;
      color: #C44D3E;
    }

    &--read {
      background-color: #E8F3E7;
      color: #5E8F5A;
    }
  }

  &__time {
    font-size: 28rpx;
    color: $c-text-sub;
    display: block;
  }

  &__chevron {
    width: 40rpx;
    height: 40rpx;
    flex-shrink: 0;
    margin-left: $sp-8;
    opacity: 0.3;
  }
}

// ── 老人端：报平安按钮 ──
.checkin-section {
  margin-bottom: $sp-32;
}

.checkin-btn {
  display: flex;
  align-items: center;
  gap: $sp-20;
  padding: $sp-24 $sp-24;
  border-radius: $r-xl;
  transition: all $duration-normal $ease-out;

  &--active {
    background: linear-gradient(135deg, $c-primary 0%, darken($c-primary, 8%) 100%);
    box-shadow: 0 8rpx 32rpx rgba($c-primary, 0.35);

    &:active {
      transform: scale(0.97);
      box-shadow: 0 4rpx 16rpx rgba($c-primary, 0.25);
    }
  }

  &--done {
    background: $c-safe-bg;
    border: 2rpx solid $c-safe;
  }

  &__icon {
    width: 64rpx;
    height: 64rpx;
    flex-shrink: 0;
  }

  &__text-wrap {
    flex: 1;
  }

  &__title {
    display: block;
    font-size: $fs-elder-title;
    font-weight: $fw-bold;
    .checkin-btn--active & { color: $c-text-inverse; }
    .checkin-btn--done & { color: $c-safe; }
  }

  &__sub {
    display: block;
    font-size: $fs-elder-body;
    margin-top: $sp-4;
    .checkin-btn--active & { color: rgba(255, 255, 255, 0.85); }
    .checkin-btn--done & { color: $c-text-sub; }
  }
}

.checkin-ripple {
  animation: ripplePulse 800ms $ease-spring both;
}

@keyframes ripplePulse {
  0% { transform: scale(1); box-shadow: 0 0 0 0 rgba($c-safe, 0.5); }
  30% { transform: scale(1.03); box-shadow: 0 0 0 20rpx rgba($c-safe, 0.3); }
  60% { transform: scale(0.98); box-shadow: 0 0 0 40rpx rgba($c-safe, 0); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba($c-safe, 0); }
}

// ── 老人端：今日菜单 ──
.menu-section {
  margin-bottom: $sp-32;
}

.menu-card {
  background: $c-surface;
  border-radius: $r-lg;
  padding: $sp-24;
  box-shadow: $shadow-sm;

  &__header {
    display: flex;
    align-items: center;
    gap: $sp-12;
    margin-bottom: $sp-20;
    padding-bottom: $sp-16;
    border-bottom: 2rpx solid $c-border-light;
  }

  &__icon {
    width: 48rpx;
    height: 48rpx;
    flex-shrink: 0;
  }

  &__title {
    font-size: $fs-elder-title;
    font-weight: $fw-bold;
    color: $c-text;
    flex: 1;
  }

  &__meal {
    font-size: $fs-body;
    color: $c-primary;
    font-weight: $fw-semibold;
    background: $c-primary-bg;
    padding: $sp-4 $sp-12;
    border-radius: $r-full;
  }

  &__dishes {
    margin-bottom: $sp-16;
  }

  &__extra {
    display: flex;
    align-items: flex-start;
    gap: $sp-12;
    padding: $sp-12 0;
    border-top: 2rpx solid $c-border-light;
  }

  &__extra-label {
    font-size: $fs-body;
    color: $c-primary;
    font-weight: $fw-semibold;
    flex-shrink: 0;
  }

  &__extra-text {
    font-size: $fs-elder-body;
    color: $c-text;
    flex: 1;
  }
}

.menu-dish {
  display: flex;
  align-items: flex-start;
  gap: $sp-12;
  padding: $sp-12 0;

  &__dot {
    width: 16rpx;
    height: 16rpx;
    border-radius: $r-full;
    margin-top: 20rpx;
    flex-shrink: 0;

    &--meat { background: $c-primary; }
    &--veg { background: $c-safe; }
  }

  &__info {
    flex: 1;
  }

  &__name {
    display: block;
    font-size: $fs-elder-body;
    font-weight: $fw-semibold;
    color: $c-text;
  }

  &__desc {
    display: block;
    font-size: $fs-body;
    color: $c-text-sub;
    margin-top: $sp-4;
  }
}

// ── 老人端：邻里帮入口 ──
.volunteer-entry {
  background: $c-surface;
  border-radius: $r-lg;
  padding: $sp-24;
  box-shadow: $shadow-sm;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $sp-32;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.98);
    background: $c-surface-warm;
  }

  &__left {
    display: flex;
    align-items: center;
    gap: $sp-16;
  }

  &__icon {
    width: 48rpx;
    height: 48rpx;
    flex-shrink: 0;
  }

  &__title {
    display: block;
    font-size: $fs-elder-body;
    font-weight: $fw-bold;
    color: $c-text;
  }

  &__desc {
    display: block;
    font-size: $fs-body;
    color: $c-text-sub;
    margin-top: $sp-4;
  }

  &__arrow {
    font-size: $fs-elder-title;
    color: $c-text-hint;
  }
}

// ── 老人端样式（大字体）──
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

.empty-state-elder {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.empty-icon-wrap-elder {
  width: 200rpx;
  height: 200rpx;
  background: $c-primary-bg;
  border-radius: $r-full;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $sp-32;
  box-shadow: $shadow-sm;
}

.empty-icon-elder {
  width: 100rpx;
  height: 100rpx;
}

.empty-title-elder {
  font-size: $fs-elder-headline;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
}

.empty-desc-elder {
  font-size: $fs-elder-body;
  color: $c-text-sub;
  margin-top: $sp-12;
  display: block;
}

// ── 老人端：牵挂卡片（与子女端统一风格）──
.elder-moment-list {
  display: flex;
  flex-direction: column;
  gap: $sp-24;
}

.elder-moment-card {
  background: $c-surface;
  border-radius: $r-lg;
  padding: $sp-24 $sp-20;
  box-shadow: $shadow-sm;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: transform $duration-normal $ease-out;

  &:active {
    transform: scale(0.98);
  }

  &__left {
    display: flex;
    align-items: center;
    gap: $sp-16;
    flex: 1;
    min-width: 0;
  }

  &__avatar {
    width: 128rpx;
    height: 128rpx;
    border-radius: $r-full;
    background-color: $c-primary-bg;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  &__avatar-text {
    font-size: $fs-elder-body;
    font-weight: $fw-bold;
    color: $c-primary;
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name-row {
    display: flex;
    align-items: center;
    gap: $sp-8;
    margin-bottom: $sp-6;
  }

  &__name {
    font-size: $fs-elder-title;
    font-weight: $fw-bold;
    color: $c-text;
  }

  &__badge {
    padding: $sp-4 $sp-12;
    border-radius: $r-full;
    font-size: $fs-body;
    font-weight: $fw-medium;
    background-color: $c-accent-bg;
    color: $c-accent;
  }

  &__time {
    font-size: $fs-elder-body;
    color: $c-text-sub;
    display: block;
  }

  &__chevron {
    width: 44rpx;
    height: 44rpx;
    flex-shrink: 0;
    margin-left: $sp-8;
    opacity: 0.4;
  }
}

// ── 底部装饰线 ──
.deco-line-wrap {
  display: flex;
  justify-content: center;
  margin-top: 96rpx;
}

.deco-line {
  width: 192rpx;
  height: 4rpx;
  background-color: rgba(#EFE9E1, 0.3);
  border-radius: $r-full;
}

// ── FAB 浮动按钮 ──
.fab {
  position: fixed;
  bottom: 180rpx;
  right: 48rpx;
  z-index: 40;
  background: #C75C3A;
  color: #FFFFFF;
  display: flex;
  align-items: center;
  gap: $sp-8;
  padding: 32rpx 48rpx;
  border-radius: $r-full;
  box-shadow: 0 8rpx 32rpx rgba(199, 92, 58, 0.35);
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.9);
    opacity: 0.9;
  }

  &__icon {
    width: 36rpx;
    height: 36rpx;
  }

  &__text {
    font-size: $fs-body;
    font-weight: $fw-medium;
    letter-spacing: 2rpx;
    color: #FFFFFF;
  }
}
</style>
