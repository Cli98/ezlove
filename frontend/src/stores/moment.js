import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { getMoments, sendMoment, deleteMoment } from "@/api/moment";

export const useMomentStore = defineStore("moment", () => {
  const moments = ref([]);
  const loading = ref(false);
  const unreadCount = computed(() => {
    const list = Array.isArray(moments.value) ? moments.value : [];
    return list.filter((m) => !m.is_read).length;
  });

  watch(unreadCount, (count) => {
    if (count > 0) {
      uni.setTabBarBadge({ index: 1, text: String(count > 99 ? "99+" : count) });
    } else {
      uni.removeTabBarBadge({ index: 1 });
    }
  });

  async function loadMoments(params = {}) {
    loading.value = true;
    try {
      const res = await getMoments(params);
      moments.value = res.items || [];
    } finally {
      loading.value = false;
    }
  }

  async function send(data) {
    const result = await sendMoment(data);
    moments.value.unshift(result);
    return result;
  }

  async function remove(id) {
    await deleteMoment(id);
    moments.value = moments.value.filter((m) => m.id !== id);
  }

  return { moments, loading, unreadCount, loadMoments, send, remove };
});
