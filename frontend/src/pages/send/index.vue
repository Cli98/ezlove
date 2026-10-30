<template>
  <view class="send-page">
    <view class="top-app-bar" :style="{ paddingTop: `${navMetrics.top}px`, paddingBottom: `${navMetrics.gap}px` }">
      <view class="top-app-bar__content" :style="{ height: `${navMetrics.height}px` }">
        <view class="top-app-bar__nav" @tap="goBack">
          <image class="nav-icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/arrow-back.png" mode="aspectFit" />
        </view>
        <view class="top-app-bar__heading app-nav-title-center">
          <text class="top-app-bar__title">发送牵挂</text>
        </view>
      </view>
    </view>

    <view class="page-body" :style="{ paddingTop: `${navMetrics.totalHeight + 12}px` }">
      <view class="section fade-in">
        <view class="section-head">
          <text class="section-head__title">发送给</text>
          <text v-if="relationStore.relations.length" class="section-head__meta">选择一位家人</text>
        </view>
        <view v-if="!relationStore.relations.length && !relationStore.loading" class="empty-recipient" @tap="goInvite">
          <view class="empty-recipient__mark">
            <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/invite.png" mode="aspectFit" />
          </view>
          <view class="empty-recipient__copy">
            <text class="empty-recipient__title">还没有绑定家人</text>
            <text class="empty-recipient__desc">邀请家人加入后，就能给 Ta 发送牵挂</text>
          </view>
          <view class="empty-recipient__action">去邀请</view>
        </view>
        <scroll-view v-else scroll-x class="recipient-scroll" :show-scrollbar="false">
          <view class="recipient-list">
            <view
              v-for="(relation, index) in relationStore.relations"
              :key="relation.id"
              class="recipient-card"
              :class="{ 'recipient-card--active': selectedElderId === relation.elder_user_id }"
              @tap="selectedElderId = relation.elder_user_id"
            >
              <image v-if="getElderAvatar(relation)" class="recipient-card__avatar" :src="getElderAvatar(relation)" mode="aspectFill" />
              <view v-else class="recipient-card__avatar recipient-card__avatar--fallback">
                <text>{{ recipientInitial(relation) }}</text>
              </view>
              <view class="recipient-card__copy">
                <text class="recipient-card__name">{{ recipientName(relation) }}</text>
                <text class="recipient-card__state">
                  {{ selectedElderId === relation.elder_user_id ? '已选择' : '点击选择' }}
                </text>
              </view>
              <view class="recipient-card__check">✓</view>
            </view>
          </view>
        </scroll-view>
      </view>

      <view class="section fade-in stagger-1">
        <view class="section-head">
          <text class="section-head__title">写一句问候</text>
          <text class="section-head__meta">最多 200 字</text>
        </view>
        <view class="letter-card">
          <image class="letter-card__watermark" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/brand/logo-mark.png" mode="aspectFit" />
          <textarea
            v-model="textContent"
            placeholder="今天想和 Ta 说点什么..."
            :maxlength="200"
            class="letter-card__input"
            placeholder-class="letter-card__placeholder"
          />
          <text class="letter-card__counter" :class="{ 'letter-card__counter--max': textContent.length >= 200 }">
            {{ textContent.length }}/200
          </text>
        </view>
      </view>

      <view class="section fade-in stagger-2">
        <view class="section-head">
          <text class="section-head__title">添加照片</text>
          <text class="section-head__meta">{{ imageUrl ? 1 : 0 }}/1</text>
        </view>
        <view v-if="!imageUrl" class="photo-add" @tap="chooseImage">
          <view class="photo-add__icon-wrap">
            <image class="photo-add__icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/add-photo.png" mode="aspectFit" />
          </view>
          <text class="photo-add__title">选择一张生活照</text>
          <text class="photo-add__desc">日常小事，就是最温暖的问候</text>
        </view>
        <view v-else class="photo-preview">
          <image :src="imageUrl" mode="aspectFill" class="photo-preview__image" />
          <view v-if="uploading" class="upload-overlay"><view class="upload-spinner" /></view>
          <view v-else class="photo-preview__remove" @tap.stop="removeImage">×</view>
          <view class="photo-preview__caption" @tap="chooseImage">重新选择</view>
        </view>
      </view>

      <view class="tips-row fade-in stagger-3">
        <view class="tip-card tip-card--amber">
          <image class="tip-card__icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/sun.png" mode="aspectFit" />
          <view class="tip-card__copy">
            <text class="tip-card__title">{{ timeOfDayHint }}</text>
            <text class="tip-card__desc">{{ timeOfDayValue }}</text>
          </view>
        </view>
        <view class="tip-card tip-card--sage">
          <image class="tip-card__icon" src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons-v2/clock.png" mode="aspectFit" />
          <view class="tip-card__copy">
            <text class="tip-card__title">发送小贴士</text>
            <text class="tip-card__desc">{{ sendTip }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="bottom-bar">
      <view class="bottom-bar__inner">
        <view class="send-button" :class="{ 'send-button--disabled': !canGenerate }" @tap="handleGenerate">
          <image src="https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/icons/send.png" mode="aspectFit" />
          <text>{{ sendButtonText }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useRelationStore } from "@/stores/relation";
import { useMomentStore } from "@/stores/moment";
import { uploadImage } from "@/api/upload";
import { requestSubscribe } from "@/utils/subscribe";
import { getNavigationBarMetrics } from "@/utils/navigation";
import { getElderAvatar } from "@/utils/avatar";

const relationStore = useRelationStore();
const momentStore = useMomentStore();
const selectedElderId = ref("");
const textContent = ref("");
const imageUrl = ref("");
const uploadedUrl = ref("");
const uploading = ref(false);
const sending = ref(false);
// 文本来自「AI 帮我写」时记为 AI 辅助生成，随牵挂一起上报，用于内容标识
const aiAssisted = ref(false);
const navMetrics = getNavigationBarMetrics();

const canGenerate = computed(
  () => (!!uploadedUrl.value || !!textContent.value.trim()) && !!selectedElderId.value && !uploading.value && !sending.value
);
const sendButtonText = computed(() => {
  if (!selectedElderId.value) return "先绑定家人";
  if (sending.value) return "发送中...";
  return "发送牵挂";
});
const timeOfDayHint = computed(() => {
  const h = new Date().getHours();
  if (h < 9) return "早晨好";
  if (h < 12) return "上午好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
});
const timeOfDayValue = computed(() => {
  const h = new Date().getHours();
  if (h < 9) return "分享一张早餐照片吧";
  if (h < 12) return "拍张照片问候长辈";
  if (h < 14) return "午后正好发一条牵挂";
  if (h < 18) return "今天过得怎么样？";
  return "晚间适合发温馨问候";
});
const sendTip = computed(() => {
  const tips = ["照片比文字更有温度", "一张生活照就是最好的问候", "长辈最爱看日常小事"];
  return tips[new Date().getDate() % tips.length];
});

onMounted(async () => {
  await relationStore.loadRelations();
  if (relationStore.relations.length > 0) selectedElderId.value = relationStore.relations[0].elder_user_id;
});

onShow(() => {
  const aiText = uni.getStorageSync("ai_suggest_text");
  if (aiText) {
    textContent.value = aiText;
    aiAssisted.value = true;
    uni.removeStorageSync("ai_suggest_text");
  }
});

function recipientName(relation) {
  return relation.elder_name || relation.relation_label || "家人";
}

function recipientInitial(relation) {
  return recipientName(relation).trim().charAt(0) || "家";
}

function removeImage() {
  imageUrl.value = "";
  uploadedUrl.value = "";
}

function chooseImage() {
  uni.chooseImage({
    count: 1,
    sizeType: ["compressed"],
    success: async (res) => {
      imageUrl.value = res.tempFilePaths[0];
      uploading.value = true;
      try {
        uploadedUrl.value = await uploadImage(res.tempFilePaths[0]);
      } catch {
        uni.showToast({ title: "图片上传失败", icon: "none" });
        removeImage();
      } finally {
        uploading.value = false;
      }
    },
  });
}

async function handleGenerate() {
  if (!canGenerate.value) {
    uni.showToast({ title: selectedElderId.value ? "写点文字或选张照片吧" : "选择要分享给谁", icon: "none" });
    return;
  }
  if (uploadedUrl.value) {
    uni.setStorageSync("poster_params", {
      image_url: uploadedUrl.value,
      user_text: textContent.value || null,
      elder_id: selectedElderId.value,
    });
    requestSubscribe(["unread"]);
    uni.navigateTo({ url: "/pages/send/poster-preview" });
    return;
  }
  sending.value = true;
  try {
    await momentStore.send({
      elder_id: selectedElderId.value,
      content_type: "text",
      text_content: textContent.value.trim(),
      is_ai_generated: aiAssisted.value,
    });
    requestSubscribe(["unread"]);
    uni.showToast({ title: "已发送", icon: "success" });
    textContent.value = "";
    setTimeout(() => uni.navigateBack(), 1200);
  } catch {
    uni.showToast({ title: "发送失败", icon: "none" });
  } finally {
    sending.value = false;
  }
}

function goBack() { uni.navigateBack(); }
function goInvite() { uni.navigateTo({ url: "/pages/bind/invite" }); }
function goAiSuggest() { uni.navigateTo({ url: `/pages/send/ai-suggest?elderId=${selectedElderId.value}` }); }
function goAiMedia() { uni.navigateTo({ url: `/pages/send/ai-media?elderId=${selectedElderId.value}` }); }
</script>

<style lang="scss" scoped>
@import "./index.scss";
</style>
