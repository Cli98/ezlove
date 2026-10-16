<template>
  <view class="contributors-page">
    <view class="hero fade-in">
      <view class="hero-deco" />
      <text class="hero-brand">易挂念</text>
      <text class="hero-title">公益志愿同学贡献页</text>
      <text class="hero-subtitle">感谢每一位让牵挂更温暖的同行者</text>
    </view>

    <view class="content">
      <view class="intro-card fade-in stagger-1">
        <text class="intro-text">
          「易挂念」是一项公益项目，由一群志愿同学利用业余时间共同打造。如需使用反馈、合作或加入我们，欢迎添加下方同学的微信。
        </text>
      </view>

      <view v-if="loading" class="state-text">名单加载中…</view>
      <view v-else-if="!contributors.length" class="state-text">名单准备中，敬请期待</view>
      <view v-else class="card-list">
        <view
          v-for="(item, index) in contributors"
          :key="item.id || item.wechat_id || index"
          class="contributor-card fade-in"
          :class="`stagger-${Math.min(index + 1, 3)}`"
        >
          <view class="avatar">{{ avatarInitial(item) }}</view>
          <view class="card-body">
            <text v-if="item.name" class="card-name">{{ item.name }}</text>
            <view class="wechat-row">
              <text class="wechat-label">微信号：</text>
              <text class="wechat-id">{{ item.wechat_id }}</text>
            </view>
            <text v-if="item.note" class="card-note">{{ item.note }}</text>
          </view>
          <view class="card-side">
            <view class="copy-btn" @tap="copyWechat(item)">复制</view>
          </view>
        </view>
      </view>

      <text class="footer-text">易挂念 · 让牵挂成为家的温度</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getContributors } from "@/api/contributor";

const contributors = ref([]);
const loading = ref(true);

onLoad(() => {
  loadContributors();
});

async function loadContributors() {
  loading.value = true;
  try {
    const data = await getContributors();
    contributors.value = Array.isArray(data) ? data : [];
  } catch {
    uni.showToast({ title: "名单加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
}

function avatarInitial(item) {
  const source = String(item.name || item.wechat_id || "益").trim();
  return source.slice(0, 1).toUpperCase();
}

function copyWechat(item) {
  uni.setClipboardData({
    data: item.wechat_id,
    success: () => uni.showToast({ title: "微信号已复制", icon: "none" }),
  });
}
</script>

<style lang="scss" scoped>
.contributors-page { min-height: 100vh; padding-bottom: 60rpx; background: $gradient-page; }
.hero { position: relative; overflow: hidden; padding: $sp-48 $sp-32 $sp-40; text-align: center; color: $c-text-inverse; background: linear-gradient(135deg, #C95746 0%, #D96A55 55%, #E38265 100%); }
.hero-deco { position: absolute; left: -120rpx; bottom: -190rpx; width: 420rpx; height: 420rpx; border-radius: 50%; background: rgba(255, 255, 255, 0.07); }
.hero-brand { display: block; font-size: $fs-caption; letter-spacing: 12rpx; opacity: 0.85; }
.hero-title { display: block; position: relative; margin-top: $sp-12; font-family: "Songti SC", "STSong", serif; font-size: $fs-headline; font-weight: $fw-bold; }
.hero-subtitle { display: block; position: relative; margin-top: $sp-12; font-size: $fs-body-sm; color: rgba(255, 250, 247, 0.88); }
.content { position: relative; z-index: 2; margin-top: -32rpx; padding: 0 $sp-24; }
.intro-card { padding: $sp-24; border: $border-subtle; border-radius: $r-xl; background: rgba(255, 255, 255, 0.92); box-shadow: $shadow-md; }
.intro-text { font-size: $fs-body-sm; line-height: $lh-relaxed; color: $c-text-sub; }
.state-text { display: block; padding: $sp-64 0; text-align: center; font-size: $fs-body-sm; color: $c-text-hint; }
.card-list { display: flex; flex-direction: column; gap: $sp-20; margin-top: $sp-20; }
.contributor-card { display: flex; align-items: center; gap: $sp-20; padding: $sp-24; border: $border-subtle; border-radius: $r-xl; background: rgba(255, 255, 255, 0.92); box-shadow: $shadow-sm; }
.avatar { display: flex; flex: none; width: 96rpx; height: 96rpx; align-items: center; justify-content: center; border-radius: 50%; background: $c-primary-bg; color: $c-primary; font-size: 40rpx; font-weight: $fw-bold; }
.card-body { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: $sp-6; }
.card-name { font-size: $fs-subtitle; font-weight: $fw-semibold; color: $c-text; }
.wechat-row { display: flex; align-items: baseline; }
.wechat-label { font-size: $fs-caption; color: $c-text-hint; }
.wechat-id { font-size: $fs-body; font-weight: $fw-medium; color: $c-text; word-break: break-all; }
.card-note { font-size: $fs-caption; color: $c-text-sub; }
.card-side { display: flex; flex: none; align-items: center; }
.copy-btn { padding: 8rpx 28rpx; border: 2rpx solid rgba($c-primary, 0.6); border-radius: $r-full; color: $c-primary; font-size: $fs-caption; &:active { background: $c-primary-bg; } }
.footer-text { display: block; margin-top: $sp-40; text-align: center; font-size: $fs-caption; color: $c-text-hint; opacity: 0.7; }
</style>
