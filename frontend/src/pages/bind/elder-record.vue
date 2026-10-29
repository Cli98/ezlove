<template>
  <view class="record-page">
    <view class="record-nav" :style="navMetrics.barStyle">
      <view class="record-nav__back" @tap="goBack">
        <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
      </view>
      <text class="app-nav-title-center" :style="navMetrics.titleStyle">社区档案</text>
    </view>

    <view class="record-body">
      <view v-if="!record" class="record-card">
        <text class="loading-text">正在加载…</text>
      </view>

      <view v-else class="record-card fade-in">
        <view class="section-icon-wrap">
          <image class="section-icon-img" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/neighbor-help.png" mode="aspectFit" />
        </view>

        <template v-if="record.bound">
          <text class="section-title">社区档案已绑定</text>
          <view class="bound-card">
            <text class="bound-name">{{ record.elder_name || '社区档案' }}</text>
            <text v-if="record.community_name" class="bound-community">{{ record.community_name }}</text>
            <text class="bound-phone" :class="{ 'is-empty': !record.phone_masked }">
              {{ record.phone_masked || '手机号未授权' }}
            </text>
          </view>
          <text class="section-desc">
            {{ record.phone_masked ? '社区名单里已能看到你的号码，需要更新时再授权一次' : '授权后社区名单会显示你的号码，工作人员联系你更方便' }}
          </text>

          <!-- #ifdef MP-WEIXIN -->
          <button
            class="btn-primary phone-btn"
            open-type="getPhoneNumber"
            :loading="binding"
            :disabled="binding"
            @getphonenumber="handleWxPhone"
          >{{ binding ? '授权中…' : (record.phone_masked ? '重新授权手机号' : '授权手机号') }}</button>
          <text class="record-hint">微信会弹窗询问是否使用手机号，点「允许」即可</text>
          <view v-if="bindError" class="bind-error">
            <text class="bind-error__title">{{ bindError.title }}</text>
            <text class="bind-error__text">{{ bindError.text }}</text>
          </view>
          <!-- #endif -->
          <!-- #ifndef MP-WEIXIN -->
          <text class="record-hint">如需更新手机号，请在微信小程序中操作或联系社区工作人员</text>
          <!-- #endif -->
        </template>

        <template v-else>
          <text class="section-title">绑定社区档案</text>
          <text class="section-desc">授权微信手机号，系统自动匹配社区登记信息，一次点击即可完成</text>

          <!-- #ifdef MP-WEIXIN -->
          <button
            class="btn-primary phone-btn"
            open-type="getPhoneNumber"
            :loading="binding"
            :disabled="binding"
            @getphonenumber="handleWxPhone"
          >{{ binding ? '绑定中…' : '一键绑定' }}</button>
          <text class="record-hint">微信会弹窗询问是否使用手机号，点「允许」即可</text>
          <view v-if="bindError" class="bind-error">
            <text class="bind-error__title">{{ bindError.title }}</text>
            <text class="bind-error__text">{{ bindError.text }}</text>
          </view>
          <text class="manual-toggle" @tap="showManual = !showManual">
            {{ showManual ? '收起手动填写' : '手机号不一致？手动填写' }}
          </text>
          <!-- #endif -->

          <view v-if="showManual" class="manual-block">
            <view class="input-wrap">
              <input
                v-model="phone"
                type="number"
                placeholder="请输入手机号"
                placeholder-class="phone-input-placeholder"
                class="phone-input"
                maxlength="11"
                :adjust-position="true"
              />
            </view>
            <view class="btn-primary bind-btn" @tap="handleBind">{{ binding ? '绑定中…' : '绑定' }}</view>
          </view>

          <text class="record-hint">手机号需与社区登记的一致；如有疑问请联系社区工作人员</text>
        </template>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useUserStore } from "@/stores/user";
import { bindElderRecord, bindElderRecordByPhoneCode, getMyCommunityRecord } from "@/api/user";
import { getNavigationBarMetrics } from "@/utils/navigation";

const userStore = useUserStore();
const navMetrics = getNavigationBarMetrics();
const phone = ref("");
const binding = ref(false);
const record = ref(null);
const bindError = ref(null);
// #ifdef MP-WEIXIN
const showManual = ref(false);
// #endif
// #ifndef MP-WEIXIN
const showManual = ref(true);
// #endif

function goBack() {
  uni.navigateBack();
}

onShow(() => {
  uni.setNavigationBarTitle({ title: "社区档案" });
  loadRecord();
});

async function loadRecord() {
  try {
    record.value = await getMyCommunityRecord();
  } catch (e) {
    // 查询失败时按未绑定展示，至少还能走手动填写
    record.value = { bound: false };
  }
}

function validPhone(value) {
  return /^1\d{10}$/.test(value);
}

// 绑定失败时按状态码给业务化说明，不把 404 这类技术码丢给用户
function bindErrorOf(e) {
  const status = e?.statusCode;
  if (status === 404) {
    return {
      title: "这个手机号还没在社区登记",
      text: "请让社区工作人员把这个号码加进你的档案后再试，也可以换一个登记过的手机号手动填写。",
    };
  }
  if (status === 409) {
    return { title: "这个微信已经绑定过档案", text: "如果显示的不是你本人，请联系社区工作人员核对。" };
  }
  if (status === 400) {
    return { title: "手机号对应多个档案", text: "请联系社区工作人员确认应该绑定哪一个。" };
  }
  return { title: "绑定没成功", text: e?.message || "请检查网络后重试，或联系社区工作人员帮忙。" };
}

async function bindByPhone(value) {
  if (binding.value) return;
  binding.value = true;
  bindError.value = null;
  try {
    const res = await bindElderRecord(value);
    await afterBound(res);
  } catch (e) {
    bindError.value = bindErrorOf(e);
    showManual.value = true;
  } finally {
    binding.value = false;
  }
}

async function afterBound(res) {
  await userStore.checkLogin();
  const tip = res.already_bound
    ? `手机号已补全 ${res.phone_masked || ""}`.trim()
    : `已绑定：${res.elder_name || "社区档案"}`;
  uni.showToast({ title: tip, icon: "success" });
  await loadRecord();
  setTimeout(() => uni.navigateBack(), 1500);
}

async function handleWxPhone(e) {
  const detail = e?.detail || {};
  const errMsg = detail.errMsg || "";
  if (errMsg !== "getPhoneNumber:ok" || !detail.code) {
    // errMsg 带具体原因（user deny / no permission / privacy ...），别一律说成“已取消”
    console.warn("[getPhoneNumber]", errMsg);
    const hints = [
      ["user deny", "已取消授权，可手动填写手机号"],
      ["privacy", "请先同意隐私授权，或手动填写手机号"],
      ["no permission", "微信手机号能力未开通，请手动填写"],
      ["access denied", "已拒绝隐私授权，可手动填写手机号"],
    ];
    const hint = hints.find(([key]) => errMsg.includes(key))?.[1];
    bindError.value = {
      title: "手机号授权没成功",
      text: hint || "请重新点「一键绑定」并选择允许，也可以手动填写手机号。",
    };
    showManual.value = true;
    return;
  }
  if (binding.value) return;
  binding.value = true;
  bindError.value = null;
  try {
    const res = await bindElderRecordByPhoneCode(detail.code);
    await afterBound(res);
  } catch (err) {
    bindError.value = bindErrorOf(err);
    showManual.value = true;
  } finally {
    binding.value = false;
  }
}

async function handleBind() {
  const value = phone.value.trim();
  if (!validPhone(value)) {
    uni.showToast({ title: "请输入正确的手机号", icon: "none" });
    return;
  }
  await bindByPhone(value);
}
</script>

<style lang="scss" scoped>
.record-page {
  min-height: 100vh;
  padding-bottom: calc(48rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background:
    radial-gradient(circle at 8% 16%, rgba($c-primary-soft, 0.08), transparent 26%),
    $c-bg;
}

.record-nav {
  box-sizing: content-box;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  position: relative;
  color: $c-text;
  font-family: "Songti SC", "STSong", serif;
  font-size: 36rpx;
  font-weight: 800;

  &__back {
    width: 72rpx;
    height: 100%;
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  image { width: 34rpx; height: 34rpx; }
}

.record-body { padding: 34rpx 28rpx 0; }

.record-card {
  background: rgba(255, 255, 255, 0.86);
  border-radius: 32rpx;
  padding: 40rpx 32rpx;
  margin-bottom: $sp-24;
  box-shadow: $shadow-md;
  border: $border-subtle;
  text-align: center;
}

.bind-error {
  margin: 22rpx 0 6rpx;
  padding: 24rpx 26rpx;
  border-radius: 20rpx;
  background: $c-primary-surface;
  border: 2rpx solid rgba($c-primary, 0.18);
  text-align: left;

  &__title { display: block; color: $c-primary-hover; font-size: 36rpx; font-weight: 700; }
  &__text { display: block; margin-top: 8rpx; color: $c-text-sub; font-size: 34rpx; line-height: 1.6; }
}

.section-icon-wrap {
  width: 100rpx;
  height: 100rpx;
  background: $gradient-warm-soft;
  border-radius: $r-2xl;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto $sp-20;
  box-shadow: $shadow-sm;
}

.section-icon-img {
  width: 48rpx;
  height: 48rpx;
}

.section-title {
  font-family: "Songti SC", "STSong", serif;
  font-size: 40rpx;
  font-weight: $fw-bold;
  color: $c-text;
  display: block;
  margin-bottom: $sp-8;
}

.section-desc {
  font-size: $fs-body;
  color: $c-text-sub;
  display: block;
  margin-bottom: $sp-32;
  line-height: 1.6;
}

.loading-text {
  display: block;
  padding: 60rpx 0;
  font-size: 36rpx;
  color: $c-text-hint;
}

.bound-card {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  margin: 28rpx 0 $sp-8;
  padding: 28rpx 24rpx;
  background: $c-bg;
  border-radius: $r-lg;
  border: $border-subtle;
}

.bound-name {
  font-size: 44rpx;
  font-weight: $fw-bold;
  color: $c-text;
}

.bound-community {
  font-size: 32rpx;
  color: $c-text-sub;
}

.bound-phone {
  margin-top: 4rpx;
  font-size: 36rpx;
  letter-spacing: 2rpx;
  color: $c-primary;

  &.is-empty { color: $c-text-hint; }
}

.input-wrap {
  margin: $sp-24 0 $sp-8;
}

.phone-input {
  width: 100%;
  height: 96rpx;
  box-sizing: border-box;
  text-align: center;
  font-size: 40rpx;
  letter-spacing: 4rpx;
  line-height: 96rpx;
  padding: 0 $sp-20;
  background: $c-bg;
  border-radius: $r-lg;
  border: $border-subtle;
  transition: border-color $duration-normal $ease-out;
}

.phone-input-placeholder {
  font-size: $fs-title;
  letter-spacing: 2rpx;
}

.bind-btn {
  width: 100%;
  margin-top: $sp-24;
}

.phone-btn {
  width: 100%;
  margin-top: $sp-24;
  border: none;

  &::after { border: none; }

  &[disabled] { opacity: 0.7; }
}

.manual-toggle {
  display: block;
  margin-top: $sp-24;
  font-size: $fs-body;
  color: $c-primary;
}

.manual-block { margin-top: $sp-8; }

.record-hint {
  display: block;
  margin-top: $sp-20;
  font-size: $fs-caption;
  color: $c-text-hint;
  line-height: 1.6;
}
</style>