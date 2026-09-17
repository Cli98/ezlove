import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { getAlerts, resolveAlert } from "@/api/alert";

export const useAlertStore = defineStore("alert", () => {
  const alerts = ref([]);
  const loading = ref(false);
  const unresolvedCount = computed(() => {
    const list = Array.isArray(alerts.value) ? alerts.value : [];
    return list.filter((a) => !a.is_resolved).length;
  });

  watch(unresolvedCount, (count) => {
    if (count > 0) {
      uni.setTabBarBadge({ index: 2, text: String(count > 99 ? "99+" : count) });
    } else {
      uni.removeTabBarBadge({ index: 2 });
    }
  });

  async function loadAlerts(params = {}) {
    loading.value = true;
    try {
      const res = await getAlerts(params);
      alerts.value = res.items || [];
    } finally {
      loading.value = false;
    }
  }

  async function resolve(id) {
    await resolveAlert(id);
    const alert = alerts.value.find((a) => a.id === id);
    if (alert) alert.is_resolved = true;
  }

  return { alerts, loading, unresolvedCount, loadAlerts, resolve };
});
