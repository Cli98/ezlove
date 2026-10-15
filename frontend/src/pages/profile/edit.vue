<template>
  <view class="edit-page">
    <view class="edit-nav" :style="navMetrics.barStyle">
      <view class="edit-nav__back" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
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
      <view class="field-block field-block--last">
        <text class="field-label">选择头像</text>
        <view class="avatar-grid">
          <view
            v-for="avatar in avatarOptions"
            :key="avatar"
            class="avatar-option"
            :class="{ 'avatar-option--active': !tempAvatar && (form.avatar_url || DEFAULT_AVATAR) === avatar }"
            @tap="selectAvatar(avatar)"
          >
            <image :src="avatar" mode="aspectFill" />
            <text v-if="!tempAvatar && (form.avatar_url || DEFAULT_AVATAR) === avatar" class="avatar-check">✓</text>
          </view>
        </view>
        <button class="upload-avatar" @tap="chooseAvatar">从相册上传头像</button>
        <text class="avatar-hint">也可以直接使用上方的默认头像</text>
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
import { uploadImage } from "@/api/upload";
import { getFamilyAvatar, getElderAvatar, getPresetAvatars, DEFAULT_AVATAR } from "@/utils/avatar";
import { getNavigationBarMetrics } from "@/utils/navigation";

const userStore = useUserStore();
const navMetrics = getNavigationBarMetrics();
const saving = ref(false);
const tempAvatar = ref("");
const form = reactive({ nickname: "", avatar_url: null });

const roleLabel = computed(() => userStore.isElder ? "长辈" : "子女 / 亲属");
const avatarOptions = computed(() => [DEFAULT_AVATAR, ...getPresetAvatars(userStore.profile?.role)]);
const previewAvatar = computed(() => {
  if (tempAvatar.value) return tempAvatar.value;
  const data = { ...userStore.profile, avatar_url: form.avatar_url };
  return userStore.isElder ? getElderAvatar(data) : getFamilyAvatar(data);
});

onLoad(async () => {
  if (!userStore.profile) await userStore.checkLogin();
  const profile = userStore.profile || {};
  form.nickname = profile.nickname || "";
  form.avatar_url = profile.avatar_url || null;
});

function selectAvatar(avatar) {
  tempAvatar.value = "";
  form.avatar_url = avatar === DEFAULT_AVATAR ? null : avatar;
}

function chooseAvatar() {
  uni.chooseImage({
    count: 1,
    sizeType: ["compressed"],
    sourceType: ["album", "camera"],
    success: ({ tempFilePaths }) => { tempAvatar.value = tempFilePaths?.[0] || ""; },
    fail: (error) => {
      if (!/cancel/i.test(error?.errMsg || "")) uni.showToast({ title: "选取照片失败", icon: "none" });
    },
  });
}

function goBack() {
  uni.navigateBack();
}

async function saveProfile() {
  const nickname = form.nickname.trim();
  if (!nickname) return uni.showToast({ title: "请填写昵称", icon: "none" });

  saving.value = true;
  try {
    const avatar_url = tempAvatar.value ? await uploadImage(tempAvatar.value, "avatar") : form.avatar_url;
    await userStore.updateProfile({ nickname, avatar_url });
    uni.showToast({ title: "资料已保存", icon: "success" });
    setTimeout(goBack, 500);
  } catch (error) {
    uni.showToast({ title: error?.message || "保存失败，请稍后重试", icon: "none" });
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
.avatar-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: $sp-12; }
.avatar-option { position: relative; display: flex; align-items: center; justify-content: center; min-height: 138rpx; border: 3rpx solid transparent; border-radius: $r-lg; background: $c-bg-warm; image { width: 112rpx; height: 112rpx; border-radius: $r-full; } }
.avatar-option--active { border-color: $c-primary; background: $c-primary-surface; }
.avatar-check { position: absolute; right: $sp-8; bottom: $sp-8; color: $c-primary; font-size: 28rpx; font-weight: $fw-bold; }
.upload-avatar { margin-top: $sp-20; border: 2rpx solid $c-primary; border-radius: $r-full; color: $c-primary; background: $c-surface; font-size: $fs-body; &::after { border: 0; } }
.avatar-hint { display: block; margin-top: $sp-12; color: $c-text-hint; font-size: $fs-caption; text-align: center; }
.sync-note { display: block; margin: $sp-20 0 $sp-16; color: $c-text-hint; font-size: $fs-caption; text-align: center; }
.save-button { display: flex; align-items: center; justify-content: center; height: 96rpx; border: 0; border-radius: $r-full; color: $c-text-inverse; background: $c-primary; box-shadow: $shadow-glow; font-size: $fs-subtitle; font-weight: $fw-bold; &::after { border: 0; } &[disabled] { opacity: 0.6; } }
</style>
