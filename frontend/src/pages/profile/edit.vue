<template>
  <view class="edit-page">
    <view class="edit-nav" :style="navMetrics.barStyle">
      <view class="edit-nav__back" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="edit-nav__title app-nav-title-center" :style="navMetrics.titleStyle">编辑资料</text>
    </view>

    <view class="profile-preview fade-in">
      <image v-if="previewAvatar" class="preview-avatar" :src="previewAvatar" mode="aspectFill" />
      <view v-else class="preview-avatar preview-avatar--fallback">
        <text>{{ previewInitial }}</text>
      </view>
      <view class="preview-copy">
        <text class="preview-name">{{ form.nickname.trim() || '给自己取个昵称' }}</text>
        <text class="preview-role">{{ roleLabel }}</text>
      </view>
    </view>

    <view class="form-card fade-in stagger-1">
      <view class="field-block">
        <text class="field-label">昵称</text>
        <view class="input-wrap">
          <input v-model="form.nickname" class="nickname-input" maxlength="20" placeholder="请输入昵称" />
          <text class="input-count">{{ form.nickname.length }}/20</text>
        </view>
      </view>

    </view>

    <text class="sync-note">保存后，家人端和社区后台会使用同一份资料</text>
    <button class="save-button" :loading="saving" :disabled="saving" @tap="saveProfile">保存资料</button>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";
import { getFullUrl } from "@/api/config";
import { getFamilyAvatar, getElderAvatar } from "@/utils/avatar";
import { getNavigationBarMetrics } from "@/utils/navigation";

const userStore = useUserStore();
const navMetrics = getNavigationBarMetrics();
const saving = ref(false);
const form = reactive({ nickname: "" });

const roleLabel = computed(() => userStore.isElder ? "长辈" : "子女 / 亲属");
const previewAvatar = computed(() => {
  const data = userStore.profile || {};
  const avatar = userStore.isElder ? getElderAvatar(data) : getFamilyAvatar(data);
  return getFullUrl(avatar);
});
const previewInitial = computed(() => (form.nickname.trim() || "我").charAt(0));

onLoad(async () => {
  if (!userStore.profile) await userStore.checkLogin();
  const profile = userStore.profile || {};
  form.nickname = profile.nickname || "";
});

function goBack() {
  uni.navigateBack();
}

async function saveProfile() {
  const nickname = form.nickname.trim();
  if (!nickname) return uni.showToast({ title: "请填写昵称", icon: "none" });

  saving.value = true;
  try {
    await userStore.updateProfile({ nickname });
    uni.showToast({ title: "资料已保存", icon: "success" });
    setTimeout(goBack, 500);
  } catch {
    uni.showToast({ title: "保存失败，请稍后重试", icon: "none" });
  } finally {
    saving.value = false;
  }
}
</script>

<style lang="scss" scoped>
.edit-page { min-height: 100vh; box-sizing: border-box; padding: 0 $sp-24 calc($sp-40 + env(safe-area-inset-bottom)); background: $gradient-page; }
.edit-nav { position: relative; box-sizing: content-box; margin: 0 (-$sp-24); }
.edit-nav__back { width: 88rpx; height: 100%; display: flex; align-items: center; justify-content: center; image { width: 34rpx; height: 34rpx; } }
.edit-nav__title { color: $c-text; font-family: "Songti SC", "STSong", serif; font-size: $fs-title; font-weight: $fw-bold; }
.profile-preview { display: flex; align-items: center; gap: $sp-20; margin: $sp-24 0; padding: $sp-24; border-radius: $r-xl; background: $gradient-warm; box-shadow: $shadow-lg; }
.preview-avatar { width: 132rpx; height: 132rpx; flex: none; border: 6rpx solid rgba($c-surface, 0.82); border-radius: $r-full; background: $c-primary-surface; box-shadow: $shadow-md; }
.preview-avatar--fallback { display: flex; align-items: center; justify-content: center; color: $c-text-inverse; font-size: 52rpx; font-weight: $fw-bold; }
.preview-copy { display: flex; flex-direction: column; gap: $sp-6; }
.preview-name { color: $c-text-inverse; font-family: "Songti SC", "STSong", serif; font-size: $fs-headline; font-weight: $fw-bold; }
.preview-role { color: rgba($c-text-inverse, 0.88); font-size: $fs-body; font-weight: $fw-semibold; }
.form-card { padding: 0 $sp-24; border: $border-subtle; border-radius: $r-xl; background: rgba($c-surface, 0.94); box-shadow: $shadow-md; }
.field-block { padding: $sp-24 0; border-bottom: 1rpx solid $c-border-light; }
.field-label { display: block; margin-bottom: $sp-12; color: $c-text; font-size: $fs-subtitle; font-weight: $fw-semibold; }
.input-wrap { display: flex; align-items: center; min-height: 88rpx; padding: 0 $sp-16; border: 2rpx solid $c-border; border-radius: $r-md; background: $c-surface-warm; }
.nickname-input { flex: 1; color: $c-text; font-size: $fs-body; }
.input-count { color: $c-text-hint; font-size: $fs-caption; }
.sync-note { display: block; margin: $sp-20 0 $sp-16; color: $c-text-hint; font-size: $fs-caption; text-align: center; }
.save-button { display: flex; align-items: center; justify-content: center; height: 96rpx; border: 0; border-radius: $r-full; color: $c-text-inverse; background: $c-primary; box-shadow: $shadow-glow; font-size: $fs-subtitle; font-weight: $fw-bold; &::after { border: 0; } &[disabled] { opacity: 0.6; } }
</style>
