<template>
  <view class="elder-reminder-page">
    <view class="elder-reminder-hero">
      <text class="elder-reminder-title">安心生活，\n不用操心提醒</text>
      <text class="elder-reminder-desc">需要留意的事情，会由家人与社区工作人员及时关心</text>
    </view>

    <view class="elder-reminder-card" @tap="goHistory">
      <image class="elder-reminder-icon" src="/static/brand/logo-mark.png" mode="aspectFit" />
      <view class="elder-reminder-copy">
        <text class="elder-reminder-card-title">看看家人的牵挂</text>
        <text class="elder-reminder-card-desc">收到的问候都保存在记录里</text>
      </view>
      <text class="elder-reminder-arrow">›</text>
    </view>
  </view>
</template>

<script setup>
function goHistory() {
  uni.switchTab({ url: "/pages/history/index" });
}
</script>

<style lang="scss" scoped>
.elder-reminder-page {
  min-height: 100vh;
  padding: calc(var(--status-bar-height, 50rpx) + 96rpx) 24rpx 170rpx;
  background:
    radial-gradient(circle at 92% 8%, rgba($c-accent, 0.11), transparent 22%),
    $gradient-page;
}

.elder-reminder-hero {
  margin: 0 12rpx 42rpx;
}

.elder-reminder-title {
  display: block;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 54rpx;
  font-weight: 900;
  line-height: 1.3;
  white-space: pre-line;
}

.elder-reminder-desc {
  display: block;
  margin-top: 18rpx;
  color: $c-text-sub;
  font-size: 32rpx;
  line-height: 1.65;
}

.elder-reminder-card {
  min-height: 140rpx;
  display: flex;
  align-items: center;
  gap: 22rpx;
  padding: 26rpx;
  border: 1rpx solid $c-border;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: $shadow-sm;
}

.elder-reminder-icon {
  width: 76rpx;
  height: 76rpx;
  flex: none;
}

.elder-reminder-copy {
  min-width: 0;
  flex: 1;
}

.elder-reminder-card-title,
.elder-reminder-card-desc {
  display: block;
}

.elder-reminder-card-title {
  color: $c-text;
  font-size: 38rpx;
  font-weight: $fw-bold;
}

.elder-reminder-card-desc {
  margin-top: 8rpx;
  color: $c-text-sub;
  font-size: 28rpx;
  line-height: 1.5;
}

.elder-reminder-arrow {
  color: $c-text-hint;
  font-size: 52rpx;
}
</style>
