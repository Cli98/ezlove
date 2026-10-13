<template>
  <!-- 昵称编辑弹窗：遮罩 + 输入 + 取消/保存 -->
  <view class="modal-mask" @tap="close">
    <view class="modal-card" @tap.stop>
      <text class="modal-title">设置昵称</text>
      <text class="modal-desc">家人会看到这个名字</text>
      <input
        v-model="nickname"
        type="text"
        class="modal-input"
        placeholder="请输入昵称"
        placeholder-style="color: #B8B0A8;"
        :maxlength="20"
        :adjust-position="true"
      />
      <view class="modal-actions">
        <view class="modal-btn modal-btn-cancel" @tap="close">
          <text>取消</text>
        </view>
        <view class="modal-btn modal-btn-confirm" :class="{ 'is-disabled': saving }" @tap="handleSave">
          <text>{{ saving ? "保存中…" : "保存" }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { useUserStore } from "@/stores/user";

const emit = defineEmits(["close"]);
const userStore = useUserStore();
const nickname = ref(userStore.profile?.nickname || "");
const saving = ref(false);

function close() {
  emit("close");
}

async function handleSave() {
  const name = nickname.value.trim();
  if (!name) {
    uni.showToast({ title: "昵称不能为空", icon: "none" });
    return;
  }
  if (name === (userStore.profile?.nickname || "")) {
    close();
    return;
  }
  if (saving.value) return;
  saving.value = true;
  try {
    await userStore.updateNickname(name);
    uni.showToast({ title: "昵称已更新", icon: "success" });
    close();
  } catch (e) {
    uni.showToast({ title: e.message || "保存失败", icon: "none" });
  } finally {
    saving.value = false;
  }
}
</script>

<style lang="scss" scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(51, 35, 25, 0.45);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 $sp-48;
}

.modal-card {
  width: 100%;
  max-width: 620rpx;
  background: $c-surface;
  border-radius: $r-xl;
  padding: $sp-40 $sp-32 $sp-24;
  box-shadow: $shadow-lg;
}

.modal-title {
  display: block;
  text-align: center;
  font-size: $fs-title;
  font-weight: $fw-bold;
  color: $c-text;
}

.modal-desc {
  display: block;
  text-align: center;
  font-size: $fs-caption;
  color: $c-text-hint;
  margin-top: $sp-8;
  margin-bottom: $sp-24;
}

.modal-input {
  width: 100%;
  height: 96rpx;
  padding: 0 $sp-24;
  background: $c-surface-warm;
  border: 2rpx solid $c-border-light;
  border-radius: $r-lg;
  font-size: $fs-body;
  color: $c-text;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  gap: $sp-16;
  margin-top: $sp-24;
}

.modal-btn {
  flex: 1;
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $r-full;
  font-size: $fs-body;
  font-weight: $fw-medium;
  transition: all $duration-normal $ease-out;

  &:active {
    transform: scale(0.97);
  }
}

.modal-btn-cancel {
  background: $c-surface-warm;
  color: $c-text-sub;
  border: 2rpx solid $c-border-light;
}

.modal-btn-confirm {
  background: $gradient-warm;
  color: $c-text-inverse;

  &.is-disabled {
    opacity: 0.6;
  }
}
</style>