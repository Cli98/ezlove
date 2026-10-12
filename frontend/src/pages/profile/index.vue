<template>
  <view class="profile-page">
    <view class="profile-hero fade-in">
      <view class="hero-deco hero-deco--bottom" />
      <image class="hero-mark" src="/static/brand/logo-mark.png" mode="aspectFit" />

      <view class="tab-nav" :style="navMetrics.barStyle" />

      <view class="hero-profile" @tap="goEditProfile">
        <view class="profile-avatar-wrap">
          <image v-if="avatarSrc" class="profile-avatar" :src="avatarSrc" mode="aspectFill" />
          <view v-else class="profile-avatar profile-avatar--fallback">
            <text>{{ (userStore.profile?.nickname || '我')[0] }}</text>
          </view>
          <view class="profile-edit-badge">编辑</view>
        </view>
        <view class="hero-copy">
          <text class="nickname">{{ userStore.profile?.nickname || '未设置昵称' }}</text>
          <text class="role-text">{{ userStore.isFamily ? '子女 / 亲属' : '长辈' }}</text>
        </view>
      </view>
      <image class="hero-slogan" src="/static/brand/profile-slogan-handwritten.png" mode="widthFix" />
    </view>

    <view class="profile-content">
      <view v-if="userStore.isFamily" class="stats-row fade-in stagger-1">
        <view class="stat-item">
          <text class="stat-num">{{ elderCount }}</text>
          <text class="stat-label">守护家人</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-num">{{ momentCount }}</text>
          <text class="stat-label">牵挂已送</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-num">{{ careStreak }}</text>
          <text class="stat-label">连续天数</text>
        </view>
      </view>

      <view class="menu-panel fade-in stagger-2">
        <template v-if="userStore.isFamily">
          <view class="menu-row" @tap="goBindList">
            <view class="menu-left">
              <view class="menu-icon">
                <image src="/static/icons/family.svg" mode="aspectFit" />
              </view>
              <view class="menu-copy">
                <text class="menu-text">我的家人</text>
                <text class="menu-desc">查看和管理已绑定的家人</text>
              </view>
            </view>
            <image class="menu-arrow-icon" src="/static/icons/chevron-right.svg" mode="aspectFit" />
          </view>
          <view class="menu-row" @tap="goInvite">
            <view class="menu-left">
              <view class="menu-icon">
                <image src="/static/icons/invite.svg" mode="aspectFit" />
              </view>
              <view class="menu-copy">
                <text class="menu-text">邀请绑定</text>
                <text class="menu-desc">邀请更多家人一起加入</text>
              </view>
            </view>
            <image class="menu-arrow-icon" src="/static/icons/chevron-right.svg" mode="aspectFit" />
          </view>
        </template>
        <view class="menu-row" @tap="goVolunteer">
          <view class="menu-left">
            <view class="menu-icon">
              <image src="/static/icons/neighbor-help.svg" mode="aspectFit" />
            </view>
            <view class="menu-copy">
              <text class="menu-text">邻里帮</text>
              <text class="menu-desc">与邻里互助，传递温暖</text>
            </view>
          </view>
          <image class="menu-arrow-icon" src="/static/icons/chevron-right.svg" mode="aspectFit" />
        </view>
        <view class="menu-row" @tap="goSwitchRole">
          <view class="menu-left">
            <view class="menu-icon">
              <image src="/static/icons/login-family.svg" mode="aspectFit" />
            </view>
            <view class="menu-copy">
              <text class="menu-text">切换身份</text>
              <text class="menu-desc">在子女/亲属与长辈身份间切换</text>
            </view>
          </view>
          <image class="menu-arrow-icon" src="/static/icons/chevron-right.svg" mode="aspectFit" />
        </view>
        <view class="menu-row" @tap="goPrivacyCenter">
          <view class="menu-left">
            <view class="menu-icon">
              <image src="/static/icons/key.svg" mode="aspectFit" />
            </view>
            <view class="menu-copy">
              <text class="menu-text">隐私与协议</text>
              <text class="menu-desc">查看用户协议与隐私政策</text>
            </view>
          </view>
          <image class="menu-arrow-icon" src="/static/icons/chevron-right.svg" mode="aspectFit" />
        </view>
      </view>

      <view class="logout-section fade-in stagger-3">
        <view class="logout-btn" @tap="handleLogout">
          <text class="logout-text">退出登录</text>
        </view>
        <text class="version-text">易挂念 v1.0.0</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";
import { getRelations } from "@/api/relation";
import { getMoments } from "@/api/moment";
import { getFullUrl } from "@/api/config";
import { getNavigationBarMetrics } from "@/utils/navigation";
import { getFamilyAvatar } from "@/utils/avatar";

const userStore = useUserStore();
const navMetrics = getNavigationBarMetrics();
const elderCount = ref(0);
const momentCount = ref(0);
const careStreak = ref(0);

const avatarSrc = computed(() => {
  const avatar = userStore.profile?.avatar_url;
  if (avatar) return getFullUrl(avatar);
  return userStore.isElder ? "" : getFamilyAvatar(userStore.profile);
});

onShow(() => {
  if (userStore.isFamily) loadStats();
});

async function loadStats() {
  try {
    const [relations, moments] = await Promise.all([
      getRelations(),
      getMoments({ limit: 200 }),
    ]);
    const momentItems = moments.items || [];
    elderCount.value = relations.length;
    momentCount.value = moments.total ?? momentItems.length;
    careStreak.value = calcStreak(momentItems);
  } catch {
    uni.showToast({ title: '数据加载失败', icon: 'none' });
  }
}

function calcStreak(moments) {
  if (!moments.length) return 0;
  const days = new Set();
  moments.forEach((m) => {
    if (m.created_at) days.add(m.created_at.slice(0, 10));
  });
  const sorted = [...days].sort().reverse();
  const today = new Date().toISOString().slice(0, 10);
  if (sorted[0] !== today) return 0;
  let streak = 1;
  for (let i = 1; i < sorted.length; i++) {
    const prev = new Date(sorted[i - 1]);
    const cur = new Date(sorted[i]);
    const diff = (prev - cur) / 86400000;
    if (diff === 1) streak++;
    else break;
  }
  return streak;
}

function goBindList() {
  uni.navigateTo({ url: "/pages/bind/list" });
}

function goInvite() {
  uni.navigateTo({ url: "/pages/bind/invite" });
}

function goVolunteer() {
  uni.navigateTo({ url: "/pages/volunteer/index" });
}

function goSwitchRole() {
  uni.navigateTo({ url: "/pages/login/role" });
}

function goEditProfile() {
  uni.navigateTo({ url: "/pages/profile/edit" });
}

function goPrivacyCenter() {
  uni.showActionSheet({
    itemList: ["用户协议", "隐私政策", "撤回同意"],
    success: (res) => {
      if (res.tapIndex === 0) uni.navigateTo({ url: "/pages/about/agreement" });
      else if (res.tapIndex === 1) uni.navigateTo({ url: "/pages/about/privacy" });
      else if (res.tapIndex === 2) confirmWithdraw();
    },
  });
}

function confirmWithdraw() {
  uni.showModal({
    title: "撤回同意",
    content: "撤回后您将退出登录，我们将停止处理您的个人信息；如需删除已收集的信息，可通过隐私政策中的联系方式联系我们。确定撤回吗？",
    confirmText: "确定撤回",
    success: (res) => {
      if (!res.confirm) return;
      userStore.logout();
      uni.showToast({ title: "已撤回同意，重新使用需再次勾选确认", icon: "none", duration: 3000 });
    },
  });
}

function handleLogout() {
  uni.showModal({
    title: "退出登录",
    content: "确定退出吗？",
    success: (res) => {
      if (res.confirm) userStore.logout();
    },
  });
}
</script>

<style lang="scss" scoped>
.profile-page { min-height: 100vh; padding-bottom: 200rpx; background: $gradient-page; }
.profile-hero { position: relative; min-height: 488rpx; overflow: hidden; color: $c-text-inverse; background: linear-gradient(135deg, #C95746 0%, #D96A55 55%, #E38265 100%); }
.tab-nav { position: relative; z-index: 2; box-sizing: content-box; }
.hero-mark { position: absolute; top: 124rpx; right: 18rpx; width: 260rpx; height: 260rpx; opacity: 0.14; filter: brightness(8); }
.hero-deco { position: absolute; border-radius: 50%; background: rgba(255, 255, 255, 0.07); }
.hero-deco--bottom { left: -120rpx; bottom: -190rpx; width: 420rpx; height: 420rpx; }
.hero-profile { position: relative; z-index: 1; display: flex; align-items: center; gap: $sp-20; padding: 0 $sp-32; }
.profile-avatar-wrap { position: relative; flex: none; }
.profile-avatar { width: 142rpx; height: 142rpx; flex: none; border-radius: 50%; border: 6rpx solid rgba(255, 255, 255, 0.82); box-shadow: 0 10rpx 30rpx rgba(78, 36, 24, 0.2); }
.profile-avatar--fallback { display: flex; align-items: center; justify-content: center; color: $c-primary; background: $c-primary-bg; font-size: 54rpx; font-weight: $fw-bold; }
.profile-edit-badge { position: absolute; right: -4rpx; bottom: 2rpx; padding: 4rpx 10rpx; border: 2rpx solid rgba(255, 255, 255, 0.9); border-radius: $r-full; color: $c-text-inverse; background: $c-primary; font-size: 20rpx; line-height: 1.4; box-shadow: $shadow-sm; }
.hero-copy { display: flex; flex-direction: column; gap: $sp-6; }
.nickname { font-family: "Songti SC", "STSong", serif; font-size: 46rpx; font-weight: $fw-bold; }
.role-text { position: relative; top: -8rpx; font-size: $fs-body-sm; font-weight: 600; color: rgba(255, 250, 247, 0.9); }
.hero-slogan { position: relative; z-index: 1; display: block; width: 186rpx; margin: -44rpx $sp-32 0 238rpx; }
.profile-content { position: relative; z-index: 3; margin-top: -72rpx; padding: 0 $sp-24; }
.stats-row { display: flex; align-items: center; justify-content: space-around; padding: 34rpx $sp-16; margin-bottom: $sp-24; border: $border-subtle; border-radius: $r-xl; background: rgba(255, 255, 255, 0.94); box-shadow: $shadow-lg; }
.stat-item { display: flex; flex: 1; flex-direction: column; align-items: center; gap: $sp-4; }
.stat-num { font-family: "Songti SC", "STSong", serif; font-size: 48rpx; font-weight: $fw-bold; color: $c-text; }
.stat-label { font-size: $fs-caption; color: $c-text-sub; }
.stat-divider { width: 1rpx; height: 62rpx; background: $c-border; }
.menu-panel { overflow: hidden; border: $border-subtle; border-radius: $r-xl; background: rgba(255, 255, 255, 0.92); box-shadow: $shadow-md; }
.menu-row { display: flex; align-items: center; justify-content: space-between; min-height: 128rpx; margin-left: $sp-24; padding: $sp-16 $sp-24 $sp-16 0; border-bottom: 1rpx solid $c-border-light; &:last-child { border-bottom: 0; } &:active { background: $c-surface-warm; } }
.menu-left { display: flex; align-items: center; gap: $sp-16; }
.menu-icon { width: 72rpx; height: 72rpx; display: flex; align-items: center; justify-content: center; border-radius: $r-md; background: $c-primary-bg; image { width: 42rpx; height: 42rpx; } }
.menu-copy { display: flex; flex-direction: column; gap: $sp-2; }
.menu-text { font-size: $fs-title; font-weight: $fw-semibold; color: $c-text; }
.menu-desc { font-size: $fs-caption; color: $c-text-hint; }
.menu-arrow-icon { width: 32rpx; height: 32rpx; opacity: 0.4; }
.logout-section { margin-top: $sp-24; }
.logout-btn { padding: $sp-20; text-align: center; border-radius: $r-lg; background: rgba(255, 255, 255, 0.72); &:active { background: $c-warn-bg; } }
.logout-text { font-size: $fs-body; font-weight: $fw-medium; color: $c-primary; }
.version-text { display: block; margin-top: $sp-20; text-align: center; font-size: $fs-caption; color: $c-text-hint; opacity: 0.55; }
</style>
