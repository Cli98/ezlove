import { defineStore } from "pinia";
import { ref } from "vue";
import {
  getMyProfile,
  getAvailableTasks,
  getMyPoints,
  registerVolunteer,
  acceptTask as apiAcceptTask,
  completeTask as apiCompleteTask,
} from "@/api/volunteer";

export const useVolunteerStore = defineStore("volunteer", () => {
  const profile = ref(null);
  const tasks = ref([]);
  const points = ref([]);
  const loading = ref(false);
  const profileLoading = ref(true);

  async function loadProfile() {
    profileLoading.value = true;
    try {
      profile.value = await getMyProfile();
    } catch {
      profile.value = null;
    } finally {
      profileLoading.value = false;
    }
  }

  async function loadTasks() {
    loading.value = true;
    try {
      tasks.value = await getAvailableTasks();
    } catch {
      tasks.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function loadPoints() {
    try {
      points.value = await getMyPoints();
    } catch {
      points.value = [];
    }
  }

  async function register() {
    const res = await registerVolunteer();
    await loadProfile();
    return res;
  }

  async function accept(taskId) {
    const res = await apiAcceptTask(taskId);
    return res;
  }

  async function complete(taskId, data) {
    const res = await apiCompleteTask(taskId, data);
    return res;
  }

  return { profile, tasks, points, loading, profileLoading, loadProfile, loadTasks, loadPoints, register, accept, complete };
});
