<template>
  <view class="edit-page">
    <view class="edit-nav" :style="navMetrics.barStyle">
      <view class="edit-nav__back" @tap="goBack">
        <image src="/static/icons/arrow-back.svg" mode="aspectFit" />
      </view>
      <text class="edit-nav__title app-nav-title-center" :style="navMetrics.titleStyle">编辑资料</text>
    </view>

    <view class="profile-preview fade-in">
      <image class="preview-avatar" :src="previewAvatar" mode="aspectFill" />
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

      <view class="field-block">
        <text class="field-label">性别</text>
        <view class="gender-row">
          <view class="gender-option" :class="{ 'gender-option--active': form.gender === 'female' }" @tap="selectGender('female')">
            <text class="gender-symbol">♀</text>
            <text>女</text>
          </view>
          <view class="gender-option" :class="{ 'gender-option--active': form.gender === 'male' }" @tap="selectGender('male')">
            <text class="gender-symbol">♂</text>
            <text>男</text>
          </view>
        </view>
      </view>

      <view class="field-block field-block--last">
        <text class="field-label">选择头像</text>
        <view v-if="avatarOptions.length" class="avatar-grid">
          <view v-for="avatar in avatarOptions" :key="avatar" class="avatar-option" :class="{ 'avatar-option--active': form.avatar_url === avatar }" @tap="form.avatar_url = avatar">
            <image :src="avatar" mode="aspectFill" />
            <view v-if="form.avatar_url === avatar" class="avatar-check">✓</view>
          </view>
        </view>
        <text v-else class="avatar-empty">先选择性别，就能挑选对应头像</text>
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
import { getFamilyAvatar, getElderAvatar, getPresetAvatars } from "@/utils/avatar";
import { getNavigationBarMetrics } from "@/utils/navigation";

const userStore = useUserStore();
const navMetrics = getNavigationBarMetrics();
const saving = ref(false);
const form = reactive({ nickname: "", gender: "", avatar_url: "" });

const roleLabel = computed(() => userStore.isElder ? "长辈" : "子女 / 亲属");
const avatarOptions = computed(() => getPresetAvatars(userStore.profile?.role, form.gender));
const previewAvatar = computed(() => {
  if (form.avatar_url) return getFullUrl(form.avatar_url);
  const data = { ...userStore.profile, gender: form.gender };
  return userStore.isElder ? getElderAvatar(data) : getFamilyAvatar(data);
});

onLoad(async () => {
  if (!userStore.profile) await userStore.checkLogin();
  const profile = userStore.profile || {};
  form.nickname = profile.nickname || "";
  form.gender = profile.gender || inferGender(profile.avatar_url);
  form.avatar_url = profile.avatar_url || getPresetAvatars(profile.role, form.gender)[0] || "";
});

function inferGender(url = "") {
  return url.match(/-(female|male)-/)?.[1] || "";
}

function selectGender(gender) {
  if (form.gender === gender) return;
  form.gender = gender;
  form.avatar_url = getPresetAvatars(userStore.profile?.role, gender)[0] || "";
}

function goBack() {
  uni.navigateBack();
}

async function saveProfile() {
  const nickname = form.nickname.trim();
  if (!nickname) return uni.showToast({ title: "请填写昵称", icon: "none" });
  if (!form.gender) return uni.showToast({ title: "请选择性别", icon: "none" });
  if (!form.avatar_url) return uni.showToast({ title: "请选择头像", icon: "none" });

  saving.value = true;
  try {
    await userStore.updateProfile({ nickname, gender: form.gender, avatar_url: form.avatar_url });
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
.preview-copy { display: flex; flex-direction: column; gap: $sp-6; }
.preview-name { color: $c-text-inverse; font-family: "Songti SC", "STSong", serif; font-size: $fs-headline; font-weight: $fw-bold; }
.preview-role { color: rgba($c-text-inverse, 0.88); font-size: $fs-body; font-weight: $fw-semibold; }
.form-card { padding: 0 $sp-24; border: $border-subtle; border-radius: $r-xl; background: rgba($c-surface, 0.94); box-shadow: $shadow-md; }
.field-block { padding: $sp-24 0; border-bottom: 1rpx solid $c-border-light; }
.field-block--last { border-bottom: 0; }
.field-label { display: block; margin-bottom: $sp-12; color: $c-text; font-size: $fs-subtitle; font-weight: $fw-semibold; }
.input-wrap { display: flex; align-items: center; min-height: 88rpx; padding: 0 $sp-16; border: 2rpx solid $c-border; border-radius: $r-md; background: $c-surface-warm; }
.nickname-input { flex: 1; color: $c-text; font-size: $fs-body; }
.input-count { color: $c-text-hint; font-size: $fs-caption; }
.gender-row { display: flex; gap: $sp-12; }
.gender-option { display: flex; flex: 1; align-items: center; justify-content: center; gap: $sp-8; min-height: 88rpx; border: 2rpx solid $c-border; border-radius: $r-md; color: $c-text-sub; background: $c-surface-warm; font-size: $fs-body; }
.gender-option--active { border-color: $c-primary; color: $c-primary; background: $c-primary-surface; box-shadow: 0 4rpx 14rpx rgba($c-primary, 0.12); }
.gender-symbol { font-size: 38rpx; font-weight: $fw-bold; }
.avatar-grid { display: flex; justify-content: space-between; gap: $sp-12; }
.avatar-option { position: relative; display: flex; flex: 1; align-items: center; justify-content: center; min-height: 176rpx; border: 3rpx solid transparent; border-radius: $r-lg; background: $c-bg-warm; image { width: 126rpx; height: 126rpx; border-radius: $r-full; } }
.avatar-option--active { border-color: $c-primary; background: $c-primary-surface; }
.avatar-check { position: absolute; right: $sp-8; bottom: $sp-8; display: flex; align-items: center; justify-content: center; width: 38rpx; height: 38rpx; border-radius: $r-full; color: $c-text-inverse; background: $c-primary; font-size: 24rpx; font-weight: $fw-bold; }
.avatar-empty { display: block; padding: $sp-20 0; color: $c-text-hint; font-size: $fs-caption; text-align: center; }
.sync-note { display: block; margin: $sp-20 0 $sp-16; color: $c-text-hint; font-size: $fs-caption; text-align: center; }
.save-button { display: flex; align-items: center; justify-content: center; height: 96rpx; border: 0; border-radius: $r-full; color: $c-text-inverse; background: $c-primary; box-shadow: $shadow-glow; font-size: $fs-subtitle; font-weight: $fw-bold; &::after { border: 0; } &[disabled] { opacity: 0.6; } }
</style>
