<template>
  <view class="page-home" :class="{ 'page-home--elder': userStore.isElder }">
    <view class="home-content">
      <!-- 大字问候区域 -->
      <view class="greeting-section fade-in">
        <view class="greeting-title" :class="{ 'greeting-title--elder': userStore.isElder }">
          <text class="greeting-title__line">{{ greeting }}，</text>
          <text class="greeting-title__line">{{ greetingHeadline }}</text>
        </view>
        <text class="greeting-sub" :class="{ 'greeting-sub--elder': userStore.isElder }">
          {{ userStore.isFamily ? '小小的问候，是最长情的陪伴' : '家人的牵挂，是最温暖的陪伴' }}
        </text>
      </view>

      <!-- 子女端：绑定家人列表 -->
      <view v-if="userStore.isFamily" class="family-home">
        <view class="family-focus-card fade-in stagger-1">
          <view class="family-focus-card__head">
            <view>
              <text class="family-focus-card__title">今天的牵挂</text>
              <text class="family-focus-card__sub">家人的近况，一目了然</text>
            </view>
            <image class="family-focus-card__heart" src="/static/brand/logo-mark.png" mode="aspectFit" />
          </view>
        <view v-if="relationStore.loading" class="loading-center fade-in">
          <view class="loading-dot-wrap">
            <view class="loading-dot" />
            <view class="loading-dot" />
            <view class="loading-dot" />
          </view>
        </view>
        <view v-else-if="displayRelations.length === 0" class="empty-state fade-in stagger-1">
          <view class="empty-icon-wrap">
            <image class="empty-icon" src="/static/icons/invite.svg" mode="aspectFit" />
          </view>
          <text class="empty-title">思念需要一个出口</text>
          <text class="empty-desc">邀请家人加入，让关心不再只放在心里</text>
          <view class="btn-primary empty-btn" @tap="goInvite">邀请家人</view>
        </view>

        <view v-else class="elder-list">
          <view
            v-for="(elder, index) in visibleRelations"
            :key="elder.id"
            class="elder-card fade-in"
            :class="'stagger-' + Math.min(index + 1, 4)"
            @tap="goElderStatus(elder)"
          >
            <view class="elder-card__left">
              <image v-if="elderAvatar(elder)" class="elder-card__avatar-image" :src="elderAvatar(elder)" mode="aspectFill" />
              <view v-else class="elder-card__avatar-image elder-card__avatar-fallback">
                <text>{{ elderInitial(elder) }}</text>
              </view>
              <view class="elder-card__info">
                <view class="elder-card__name-row">
                  <text class="elder-card__name">{{ elder.elder_name || elder.relation_label || '家人' }}</text>
                </view>
                <view class="elder-card__status" :class="{ 'elder-card__status--read': elder.today_read }">
                  <u-icon :name="elder.today_read ? 'checkmark-circle-fill' : 'clock-fill'" :color="elder.today_read ? '#6B9A72' : '#7E8790'" size="18" />
                  <text>{{ elder.today_read ? '今天已看到' : '还没看到' }}</text>
                </view>
                <text class="elder-card__time">{{ elder.last_active_text || (elder.today_read ? '1小时前' : '上次查看：昨天') }}</text>
              </view>
            </view>
          </view>
          </view>
          <view v-if="displayRelations.length > 0" class="family-send-btn" @tap="goSend">
            <image class="family-send-btn__icon" src="/static/icons/send.svg" mode="aspectFit" />
            <view>
              <text class="family-send-btn__title">发一条牵挂</text>
              <text class="family-send-btn__sub">一句问候，让爱不缺席</text>
            </view>
          </view>
        </view>

        <view v-if="familyRecentMoments.length" class="recent-card fade-in stagger-2">
          <view class="recent-card__head">
            <text class="recent-card__title">最近动态</text>
            <text class="recent-card__more" @tap="goHistory">查看更多 ›</text>
          </view>
          <view v-for="(m, index) in familyRecentMoments" :key="m.id" class="recent-item">
            <view class="recent-item__dot" :class="{ 'recent-item__dot--read': m.is_read }" />
            <image v-if="elderAvatar(m)" class="recent-item__avatar" :src="elderAvatar(m)" mode="aspectFill" />
            <view v-else class="recent-item__avatar recent-item__avatar--fallback">
              <text>{{ elderInitial(m) }}</text>
            </view>
            <view class="recent-item__body">
              <text class="recent-item__title">{{ elderDisplayName(m) }}{{ m.is_read ? ' 看到了你的牵挂' : ' 还没看到这条牵挂' }}</text>
              <text class="recent-item__content">{{ m.text_content || '你发送了一份牵挂' }}</text>
            </view>
            <text v-if="m.created_at_text" class="recent-item__time">{{ m.created_at_text }}</text>
          </view>
        </view>
      </view>

      <!-- 老人端：查看子女发来的牵挂 -->
      <view v-else class="elder-home">
        <view v-if="momentStore.loading" class="loading-center fade-in">
          <view class="loading-dot-wrap">
            <view class="loading-dot" />
            <view class="loading-dot" />
            <view class="loading-dot" />
          </view>
        </view>

        <view v-else-if="latestMoment" class="elder-letter-card fade-in stagger-1" @tap="goViewDetail(latestMoment)">
          <view class="elder-letter-card__head">
            <image
              v-if="senderAvatar(latestMoment)"
              class="elder-letter-card__avatar-image"
              :src="senderAvatar(latestMoment)"
              mode="aspectFill"
            />
            <view v-else class="elder-letter-card__avatar-image elder-letter-card__avatar-fallback">
              <text>{{ (latestMoment.sender_name || '家')[0] }}</text>
            </view>
            <view class="elder-letter-card__meta">
              <text class="elder-letter-card__title">{{ latestMoment.sender_name || '家人' }}发来一条牵挂</text>
              <text class="elder-letter-card__time">{{ formatRelativeTime(latestMoment.created_at) }}</text>
            </view>
          </view>
          <text class="elder-letter-card__content">{{ latestMoment.text_content || '打开看看家人想对您说的话吧。' }}</text>
        </view>

        <!-- 报平安按钮 -->
        <view class="checkin-section fade-in stagger-2">
          <view
            class="checkin-btn"
            :class="[checkedInToday ? 'checkin-btn--done' : 'checkin-btn--active', { 'checkin-ripple': showRipple }]"
            @tap="handleCheckIn"
          >
            <u-icon
              :name="checkedInToday ? 'checkmark-circle-fill' : 'heart-fill'"
              :color="checkedInToday ? '#5F8E68' : '#FFFFFF'"
              size="35"
            />
            <view class="checkin-btn__text-wrap">
              <text class="checkin-btn__title">{{ checkedInToday ? '今天已报平安' : '我今天很好' }}</text>
              <text class="checkin-btn__sub">{{ checkedInToday ? checkinTimeText : '点一下，让关心你的人放心' }}</text>
            </view>
          </view>
        </view>

        <view v-if="!momentStore.loading && !latestMoment" class="empty-state-elder fade-in stagger-1">
          <image class="empty-icon-elder" src="/static/brand/logo-mark.png" mode="aspectFit" />
          <view class="empty-copy-elder">
            <text class="empty-title-elder">今天还没有新的牵挂</text>
            <text class="empty-desc-elder">家人正在准备给您的问候呢</text>
          </view>
        </view>

        <!-- 今日菜单 -->
        <view v-if="todayMenuDishes.length" class="menu-section fade-in stagger-3">
          <view class="menu-card">
            <view class="menu-card__header">
              <u-icon name="grid-fill" color="#D48727" size="27" />
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
        <view class="volunteer-entry fade-in stagger-3" @tap="goVolunteer">
          <view class="volunteer-entry__left">
            <image class="volunteer-entry__icon" src="/static/icons/neighbor-help.svg" mode="aspectFit" />
            <view class="volunteer-entry__info">
              <text class="volunteer-entry__title">邻里帮</text>
              <text class="volunteer-entry__desc">帮助邻居，赚取积分</text>
            </view>
          </view>
          <text class="volunteer-entry__arrow">›</text>
        </view>

      </view>
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
import { getFullUrl } from "@/api/config";
import { getElderAvatar, getFamilyAvatar } from "@/utils/avatar";
import { formatRelativeTime } from "@/utils/date";

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
const latestMoment = computed(() => momentStore.moments[0] || null);
const familyRecentMoments = computed(() => momentStore.moments.slice(0, 3));
const displayRelations = computed(() => relationStore.relations);
const visibleRelations = computed(() => displayRelations.value.slice(0, 2));
function relatedElder(person) {
  const elderId = person?.elder_user_id || person?.elder_id;
  return displayRelations.value.find((item) => item.elder_user_id === elderId);
}

function elderAvatar(person, index = 0) {
  const relation = relatedElder(person);
  return getElderAvatar(relation ? { ...person, ...relation } : person, index);
}

function elderDisplayName(person) {
  const relation = relatedElder(person);
  return relation?.elder_name || relation?.relation_label || person?.elder_nickname || person?.elder_label || "家人";
}

function elderInitial(person) {
  return elderDisplayName(person).trim().charAt(0) || "家";
}

function senderAvatar(moment) {
  return moment?.sender_avatar_url ? getFullUrl(moment.sender_avatar_url) : "";
}

const menuMealLabel = computed(() => {
  const type = todayMenus.value[0]?.meal_type;
  return { breakfast: "早餐", lunch: "午餐", dinner: "晚餐" }[type] || "";
});

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
});

const greetingHeadline = computed(() => {
  if (userStore.isFamily) return "今天也记得问候家人";
  return userStore.profile?.nickname || "今天也要开开心心";
});


function formatCheckinTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  const h = d.getHours().toString().padStart(2, "0");
  const m = d.getMinutes().toString().padStart(2, "0");
  return `${h}:${m} 已报平安`;
}

async function loadCheckinStatus() {
  checkedInToday.value = false;
  checkinTimeText.value = "";
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
  if (userStore.isFamily) {
    alertStore.loadAlerts();
    relationStore.loadRelations();
    momentStore.loadMoments();
  } else {
    alertStore.clear();
    momentStore.loadMoments();
    loadCheckinStatus();
    loadTodayMenu();
  }
});

onPullDownRefresh(async () => {
  try {
    if (userStore.isFamily) {
      await Promise.all([alertStore.loadAlerts(), relationStore.loadRelations(), momentStore.loadMoments()]);
    } else {
      alertStore.clear();
      await momentStore.loadMoments();
      await loadCheckinStatus();
      await loadTodayMenu();
    }
  } finally {
    uni.stopPullDownRefresh();
  }
});

async function loadTodayMenu() {
  todayMenus.value = [];
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

function goHistory() {
  uni.switchTab({ url: "/pages/history/index" });
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

// ── 管理后台品牌语言的移动端映射 ──
.page-home,
.top-bar {
  background: $c-bg;
}

.top-bar {
  border-bottom: 1rpx solid rgba($c-border, 0.7);

  &__logo { width: 48rpx; height: 48rpx; }
  &__brand {
    font-family: "Songti SC", "STSong", serif;
    font-size: 36rpx;
    font-weight: $fw-bold;
    color: $c-text;
    letter-spacing: 4rpx;
  }
  &__right { display: flex; align-items: center; gap: 8rpx; }
  &__avatar { width: 64rpx; height: 64rpx; background: $c-primary-bg; }
  &__avatar-text { color: $c-primary; }
}

.home-content {
  padding-left: 32rpx;
  padding-right: 32rpx;
}

.greeting-section {
  margin-bottom: 40rpx;
  padding-top: 24rpx;
}

.greeting-title {
  white-space: pre-line;
  font-family: "Songti SC", "STSong", serif;
  font-size: 58rpx;
  line-height: 1.28;

  &--elder { font-size: 68rpx; }
}

.greeting-sub {
  display: block;
  margin-top: 12rpx;
  color: $c-text-hint;

  &--elder { font-size: 32rpx; }
}

.family-focus-card {
  position: relative;
  padding: 32rpx;
  border: 1rpx solid rgba($c-primary, 0.12);
  border-radius: 32rpx;
  background:
    radial-gradient(circle at 92% 6%, rgba(255, 255, 255, 0.22), transparent 28%),
    linear-gradient(145deg, #D96A4F 0%, #E58C6D 100%);
  box-shadow: 0 14rpx 38rpx rgba($c-primary, 0.14);

  &__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 28rpx;
  }

  &__title {
    display: block;
    font-family: "Songti SC", "STSong", serif;
    font-size: 48rpx;
    font-weight: $fw-bold;
    color: #fff;
  }

  &__sub { display: block; margin-top: 4rpx; font-size: 26rpx; color: rgba(255, 255, 255, 0.82); }
  &__heart { width: 92rpx; height: 92rpx; opacity: 0.18; filter: brightness(10); }
}

.family-focus-card .elder-list { gap: 16rpx; }
.family-focus-card .elder-card {
  padding: 24rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.76);
  border-radius: 24rpx;
  background: rgba(255, 252, 249, 0.94);
  box-shadow: none;
}
.family-focus-card .elder-card__avatar { width: 88rpx; height: 88rpx; }
.family-focus-card .elder-card__name { font-size: 32rpx; }

.family-send-btn {
  min-height: 104rpx;
  margin-top: 20rpx;
  padding: 18rpx 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18rpx;
  border-radius: 22rpx;
  color: #fff;
  background: linear-gradient(135deg, #B84335 0%, #C9573E 100%);
  box-shadow: 0 8rpx 20rpx rgba(#8F3027, 0.2);

  &__icon { width: 60rpx; height: 60rpx; filter: brightness(10); }
  &__title { display: block; font-size: 34rpx; font-weight: $fw-bold; }
  &__sub { display: block; margin-top: 2rpx; font-size: 22rpx; color: rgba(255, 255, 255, 0.76); }
}

.recent-card {
  margin-top: 24rpx;
  padding: 28rpx;
  border: 1rpx solid $c-border;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: $shadow-sm;

  &__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8rpx; }
  &__title { font-family: "Songti SC", "STSong", serif; font-size: 36rpx; font-weight: $fw-bold; color: $c-text; }
  &__more { font-size: 24rpx; color: $c-text-hint; }
}

.recent-item {
  display: flex;
  gap: 18rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid $c-border-light;

  &:last-child { border-bottom: 0; padding-bottom: 4rpx; }
  &__dot { width: 14rpx; height: 14rpx; margin-top: 12rpx; flex: none; border-radius: 50%; background: $c-accent; }
  &__dot--read { background: $c-safe; }
  &__body { min-width: 0; flex: 1; }
  &__title { display: block; font-size: 28rpx; font-weight: $fw-semibold; color: $c-text; }
  &__content { display: block; margin-top: 4rpx; overflow: hidden; color: $c-text-hint; font-size: 24rpx; text-overflow: ellipsis; white-space: nowrap; }
}

.elder-letter-card {
  margin-bottom: 24rpx;
  padding: 28rpx;
  border: 1rpx solid $c-border;
  border-radius: 30rpx;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 8rpx 28rpx rgba(57, 45, 36, 0.06);

  &__head { display: flex; align-items: center; gap: 20rpx; }
  &__avatar { width: 88rpx; height: 88rpx; display: flex; align-items: center; justify-content: center; flex: none; border-radius: 50%; color: $c-primary; background: $c-primary-bg; font-size: 36rpx; font-weight: $fw-bold; }
  &__meta { min-width: 0; flex: 1; }
  &__title { display: block; color: $c-text; font-family: "Songti SC", "STSong", serif; font-size: 38rpx; font-weight: $fw-bold; }
  &__time { display: block; margin-top: 4rpx; color: $c-text-hint; font-size: 26rpx; }
  &__content { display: block; margin-top: 24rpx; padding: 24rpx; border-radius: 20rpx; color: $c-text; background: $c-bg-warm; font-size: $fs-elder-body; line-height: 1.75; }
  &__action { display: block; margin-top: 20rpx; color: $c-primary; font-size: 30rpx; font-weight: $fw-semibold; text-align: right; }
}

.checkin-btn {
  border-radius: 24rpx;

  &--active { background: linear-gradient(135deg, #6B8F71 0%, #56826A 100%); box-shadow: 0 8rpx 26rpx rgba($c-safe, 0.25); }
  &__title { font-size: 44rpx; }
  &__sub { font-size: 28rpx; }
}

.menu-card,
.volunteer-entry {
  border: 1rpx solid $c-border;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.82);
}

.empty-state-elder { padding: 48rpx 0; }
.empty-icon-wrap-elder { width: 128rpx; height: 128rpx; margin-bottom: 20rpx; }
.empty-icon-elder { width: 64rpx; height: 64rpx; }
.empty-title-elder { font-size: 44rpx; }
.empty-desc-elder { font-size: 30rpx; }

// ── 视觉稿还原 ──
.page-home {
  background:
    radial-gradient(circle at 94% 10%, rgba(212, 162, 78, 0.08), transparent 28%),
    $c-bg;
}

.top-bar {
  position: absolute;
  height: auto;
  justify-content: flex-end;
  padding: calc(var(--status-bar-height, 50rpx) + 138rpx) 34rpx 0;
  border: 0;
  background: transparent;

  &__right {
    gap: 12rpx;
    padding-right: 2rpx;
  }

  &__avatar-image {
    width: 70rpx;
    height: 70rpx;
    flex: none;
    border: 4rpx solid rgba(255, 255, 255, 0.86);
    border-radius: 50%;
    box-shadow: 0 4rpx 14rpx rgba(44, 40, 37, 0.12);
  }

  &__identity { display: flex; flex-direction: column; align-items: flex-start; }
  &__name { color: $c-text; font-size: 25rpx; font-weight: 700; }
  &__role { margin-top: 2rpx; color: $c-text-hint; font-size: 18rpx; }
}

.font-size-pill {
  height: 64rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 0 22rpx;
  border: 1rpx solid $c-border;
  border-radius: 32rpx;
  color: #535B63;
  background: rgba(255, 255, 255, 0.72);
  font-size: 25rpx;
}

.home-content {
  padding: calc(var(--status-bar-height, 50rpx) + 96rpx) 24rpx 170rpx;
}

.greeting-section {
  width: 510rpx;
  margin-bottom: 30rpx;
  margin-left: 12rpx;
  padding: 0;
}

.greeting-title {
  margin: 0;
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: 50rpx;
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: 0;

  &--elder { font-size: 58rpx; }

  &__line { display: block; }
}

.greeting-sub {
  margin-top: 10rpx;
  color: #78808A;
  font-size: 25rpx;

  &--elder { font-size: 27rpx; }
}

.family-focus-card {
  padding: 26rpx;
  border: 2rpx solid rgba($c-accent, 0.34);
  border-radius: 28rpx;
  background:
    radial-gradient(circle at 96% 2%, rgba($c-primary-soft, 0.08), transparent 30%),
    linear-gradient(100deg, rgba($c-primary-soft, 0.1) 0%, rgba($c-accent, 0.05) 55%, rgba($c-surface, 0.75) 100%),
    $c-primary-surface;
  box-shadow:
    inset 0 0 0 2rpx rgba($c-surface, 0.72),
    0 12rpx 34rpx rgba(80, 53, 37, 0.07);

  &__head { position: relative; z-index: 1; min-height: 116rpx; margin-bottom: 22rpx; }
  &__title { color: $c-text; font-size: 46rpx; }
  &__sub { color: $c-text-sub; font-size: 24rpx; }
  &__heart {
    position: absolute;
    top: -6rpx;
    right: 0;
    width: 132rpx;
    height: 132rpx;
    opacity: 0.14;
    filter: brightness(0) saturate(100%) invert(57%) sepia(19%) saturate(1285%) hue-rotate(316deg) brightness(94%) contrast(76%);
    pointer-events: none;
  }
}

.family-focus-card .empty-state {
  border: 2rpx solid rgba($c-primary-soft, 0.16);
  background: rgba($c-surface, 0.9);
}

.family-focus-card .elder-list {
  flex-direction: row;
  gap: 14rpx;
}

.family-focus-card .elder-card {
  min-width: 0;
  flex: 1;
  padding: 20rpx;
  border: 2rpx solid rgba($c-primary-soft, 0.22);
  border-radius: 22rpx;
  align-items: flex-start;
  background: rgba($c-surface-warm, 0.82);
  box-shadow: 0 5rpx 16rpx rgba(80, 53, 37, 0.05);
}

.family-focus-card .elder-card__left {
  width: 100%;
  flex-direction: column;
  align-items: flex-start;
  gap: 10rpx;
}

.elder-card__avatar-image {
  width: 112rpx;
  height: 112rpx;
  border: 4rpx solid rgba($c-primary, 0.08);
  border-radius: 50%;
  background: $c-primary-surface;
  box-shadow: 0 3rpx 10rpx rgba(80, 53, 37, 0.08);
}

.elder-card__avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: $c-text-inverse;
  background: $c-primary;
  font-size: 40rpx;
  font-weight: $fw-bold;
}

.family-focus-card .elder-card__name { max-width: none; font-size: 32rpx; }
.elder-card__status { display: flex; align-items: center; gap: 8rpx; color: #7E8790; font-size: 24rpx; white-space: nowrap; }
.elder-card__status--read { color: #5F8E68; }
.family-focus-card .elder-card__time { margin-top: 5rpx; font-size: 20rpx; }

.family-send-btn {
  min-height: 112rpx;
  margin-top: 18rpx;
  border: 1rpx solid rgba($c-primary-hover, 0.12);
  border-radius: 22rpx;
  background: linear-gradient(135deg, $c-primary 0%, $c-primary-soft 100%);
  box-shadow:
    inset 0 2rpx 0 rgba(255, 255, 255, 0.16),
    0 8rpx 18rpx rgba($c-primary, 0.18);

  &__icon { width: 60rpx; height: 60rpx; filter: none; }
  &__title { font-size: 36rpx; text-shadow: 0 2rpx 4rpx rgba(82, 20, 16, 0.16); }
  &__sub { font-size: 22rpx; color: rgba(255, 255, 255, 0.84); }
}

.recent-card {
  margin-top: 22rpx;
  padding: 24rpx 28rpx;
  border-radius: 26rpx;

  &__title { font-size: 38rpx; }
}

.recent-item {
  position: relative;
  align-items: center;
  gap: 16rpx;
  padding: 15rpx 0 15rpx 28rpx;

  &:not(:last-child)::after {
    content: "";
    position: absolute;
    z-index: 0;
    left: 6rpx;
    top: calc(50% + 7rpx);
    bottom: calc(-50% - 7rpx);
    width: 2rpx;
    background: #E4D9CE;
  }
}

.recent-item__dot {
  position: absolute;
  z-index: 1;
  left: 0;
  top: 50%;
  width: 14rpx;
  height: 14rpx;
  box-sizing: border-box;
  border: 4rpx solid $c-accent;
  border-radius: 50%;
  background: #FFFFFF;
  transform: translateY(-50%);
}

.recent-item__dot--read { border-color: $c-safe; }

.recent-item__avatar {
  width: 72rpx;
  height: 72rpx;
  flex: none;
  border-radius: 50%;
}

.recent-item__avatar--fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: $c-text-inverse;
  background: $c-primary;
  font-size: 28rpx;
  font-weight: $fw-bold;
}

.recent-item__title { font-size: 25rpx; }
.recent-item__content { font-size: 21rpx; }
.recent-item__time {
  align-self: flex-start;
  flex: none;
  margin-top: 2rpx;
  color: $c-text-hint;
  font-size: 20rpx;
}

.elder-letter-card {
  padding: 24rpx;
  border-radius: 28rpx;

  &__avatar-image {
    width: 86rpx;
    height: 86rpx;
    flex: none;
    border-radius: 50%;
  }

  &__avatar-fallback {
    display: flex;
    align-items: center;
    justify-content: center;
    color: $c-primary;
    background: $c-primary-bg;
    font-size: 36rpx;
    font-weight: $fw-bold;
  }

  &__title { font-size: 37rpx; }
  &__time { font-size: 24rpx; }
  &__content {
    margin-top: 22rpx;
    padding: 24rpx;
    font-family: "Songti SC", "STSong", "SimSun", serif;
    font-size: 36rpx;
    line-height: 1.65;
  }
}

.checkin-section { margin-bottom: 24rpx; }
.checkin-btn {
  min-height: 118rpx;
  justify-content: center;
  gap: 22rpx;
  padding: 20rpx 28rpx;
  border-radius: 25rpx;

  &--active { background: linear-gradient(135deg, #77A579 0%, #58865F 100%); }
  &__text-wrap { flex: none; }
  &__title { font-family: "Songti SC", "STSong", serif; font-size: 42rpx; }
  &__sub { font-size: 24rpx; text-align: center; }
}

.menu-section { margin-bottom: 22rpx; }
.menu-card {
  padding: 24rpx;
  border-radius: 27rpx;

  &__header { margin-bottom: 10rpx; padding-bottom: 14rpx; }
  &__title { font-family: "Songti SC", "STSong", serif; font-size: 40rpx; }
  &__meal { font-size: 24rpx; }
}

.menu-dish { padding: 10rpx 0; }
.menu-dish__name { font-size: 30rpx; }
.menu-dish__desc { font-size: 24rpx; }

.volunteer-entry {
  padding: 22rpx 24rpx;
  border-radius: 26rpx;
}

.greeting-title--elder {
  font-size: 54rpx;
  line-height: 1.22;
}

.elder-home .loading-center {
  padding: 28rpx 0;
}

.empty-state-elder {
  min-height: 128rpx;
  margin-bottom: 24rpx;
  padding: 24rpx 26rpx;
  box-sizing: border-box;
  flex-direction: row;
  align-items: center;
  gap: 22rpx;
  border: 1rpx solid $c-border;
  border-radius: 26rpx;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: $shadow-sm;
}

.empty-icon-elder {
  width: 76rpx;
  height: 76rpx;
  flex: none;
}

.empty-copy-elder {
  min-width: 0;
  flex: 1;
}

.empty-title-elder {
  font-family: "Songti SC", "STSong", serif;
  font-size: 34rpx;
}

.empty-desc-elder {
  margin-top: 6rpx;
  font-size: 26rpx;
}
</style>
