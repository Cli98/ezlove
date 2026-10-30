<template>
  <view class="guest">
    <view class="guest__hero">
      <image class="guest__mark" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/brand/logo-mark.png" mode="aspectFit" />
      <text class="guest__title">易挂念</text>
      <text class="guest__slogan">把今天的牵挂，送到家人身边</text>
    </view>

    <view class="guest__preview">
      <view class="guest__preview-head">
        <view class="guest__preview-avatar">家</view>
        <view class="guest__preview-meta">
          <text class="guest__preview-name">女儿发来一条牵挂</text>
          <text class="guest__preview-time">今天 09:12</text>
        </view>
      </view>
      <text class="guest__preview-text">“今天降温了，记得多穿一件。晚上我给您打电话。”</text>
      <view class="guest__preview-foot">
        <text class="guest__preview-tag">示例内容</text>
        <text class="guest__preview-read">长辈已看到 ✓</text>
      </view>
    </view>

    <view class="guest__features">
      <view v-for="item in features" :key="item.title" class="guest__feature">
        <image class="guest__feature-icon" :src="item.icon" mode="aspectFit" />
        <view class="guest__feature-copy">
          <text class="guest__feature-title">{{ item.title }}</text>
          <text class="guest__feature-desc">{{ item.desc }}</text>
        </view>
      </view>
    </view>

    <view class="guest__actions">
      <button class="guest__login" @tap="goLogin">
        <u-icon name="weixin-fill" color="#FFFFFF" size="24" />
        <text class="guest__login-text">微信一键登录</text>
      </button>
      <text class="guest__note">可以先看看介绍，需要时再登录</text>
      <view class="guest__agreement">
        <text>登录即表示同意</text>
        <text class="guest__link" @tap.stop="openAgreement">《用户协议》</text>
        <text>与</text>
        <text class="guest__link" @tap.stop="openPrivacy">《隐私政策》</text>
      </view>
    </view>
  </view>
</template>

<script setup>
const features = [
  {
    icon: "https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/send.png",
    title: "发一条牵挂",
    desc: "一句话、一张照片，家人都能收到",
  },
  {
    icon: "https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/family.png",
    title: "看见家人的近况",
    desc: "知道长辈今天有没有看到你的问候",
  },
  {
    icon: "https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/neighbor-help.png",
    title: "社区关怀同在",
    desc: "社区工作人员和志愿者一起照看",
  },
];

function goLogin() {
  uni.navigateTo({
    url: `/pages/login/index?redirect=${encodeURIComponent("/pages/index/index")}`,
  });
}

function openAgreement() {
  uni.navigateTo({ url: "/pages/about/agreement" });
}

function openPrivacy() {
  uni.navigateTo({ url: "/pages/about/privacy" });
}
</script>

<style lang="scss" scoped>
.guest {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: calc(88rpx + env(safe-area-inset-top)) $sp-24 calc(48rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background: $c-bg;
}

.guest__hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.guest__mark {
  width: 128rpx;
  height: 128rpx;
}

.guest__title {
  margin-top: $sp-16;
  color: $c-text;
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: 72rpx;
  font-weight: 900;
  letter-spacing: 6rpx;
}

.guest__slogan {
  margin-top: $sp-12;
  color: $c-text-sub;
  font-size: 30rpx;
  line-height: 1.6;
}

.guest__preview {
  margin-top: 48rpx;
  padding: $sp-24;
  border: 1rpx solid rgba($c-primary, 0.16);
  border-radius: $r-lg;
  background: linear-gradient(135deg, #FFFDFB, $c-primary-bg);
  box-shadow: $shadow-sm;
}

.guest__preview-head {
  display: flex;
  align-items: center;
  gap: $sp-16;
}

.guest__preview-avatar {
  width: 72rpx;
  height: 72rpx;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba($c-primary, 0.12);
  color: $c-primary;
  font-size: 30rpx;
  font-weight: $fw-bold;
}

.guest__preview-meta {
  display: flex;
  flex-direction: column;
}

.guest__preview-name {
  color: $c-text;
  font-size: 30rpx;
  font-weight: 600;
}

.guest__preview-time {
  margin-top: 4rpx;
  color: $c-text-hint;
  font-size: 22rpx;
}

.guest__preview-text {
  display: block;
  margin-top: $sp-16;
  color: $c-text;
  font-size: 30rpx;
  line-height: 1.7;
}

.guest__preview-foot {
  margin-top: $sp-16;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.guest__preview-tag {
  padding: 4rpx 14rpx;
  border-radius: $r-full;
  background: rgba($c-primary, 0.1);
  color: $c-primary;
  font-size: 20rpx;
}

.guest__preview-read {
  color: #6B9A72;
  font-size: 22rpx;
}

.guest__features {
  display: flex;
  flex-direction: column;
  gap: $sp-16;
  margin-top: 40rpx;
}

.guest__feature {
  display: flex;
  align-items: center;
  gap: $sp-20;
  padding: $sp-20 $sp-24;
  border: 1rpx solid $c-border-light;
  border-radius: $r-lg;
  background: $c-surface;
}

.guest__feature-icon {
  width: 64rpx;
  height: 64rpx;
  flex: none;
}

.guest__feature-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.guest__feature-title {
  color: $c-text;
  font-size: 32rpx;
  font-weight: $fw-bold;
}

.guest__feature-desc {
  margin-top: 6rpx;
  color: $c-text-sub;
  font-size: 26rpx;
  line-height: 1.5;
}

.guest__actions {
  margin-top: auto;
  padding-top: 56rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.guest__login {
  width: 100%;
  height: 108rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14rpx;
  border: 0;
  border-radius: $r-full;
  background: linear-gradient(100deg, #C44D3E 0%, #E47A5F 100%);
  box-shadow: $shadow-glow;

  &:active {
    transform: scale(0.98);
    opacity: 0.92;
  }

  &::after {
    border: 0;
  }
}

.guest__login-text {
  color: $c-text-inverse;
  font-size: 32rpx;
  font-weight: $fw-bold;
  letter-spacing: 2rpx;
}

.guest__note {
  margin-top: $sp-16;
  color: $c-text-hint;
  font-size: 24rpx;
}

.guest__agreement {
  margin-top: $sp-8;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  color: $c-text-hint;
  font-size: 22rpx;
}

.guest__link {
  color: $c-primary;
}
</style>