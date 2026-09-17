<template>
  <div>
    <!-- SideNavBar -->
    <aside v-show="!dashboardStore.presentationMode" class="w-60 h-screen fixed left-0 top-0 bg-charcoal text-white flex flex-col py-6 gap-2 z-50">
      <div class="px-6 mb-8">
        <h1 class="font-headline font-bold text-2xl text-white">易挂念</h1>
        <p class="text-xs opacity-60 tracking-widest mt-1">社区康养管理系统</p>
      </div>
      <nav class="flex flex-col gap-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'flex items-center gap-3 px-4 py-3 rounded-lg mx-3 transition-colors relative',
            route.path === item.path || (item.path !== '/dashboard' && route.path.startsWith(item.path))
              ? 'bg-primary text-white'
              : 'text-white/60 hover:bg-white/10'
          ]"
        >
          <span class="material-symbols-outlined">{{ item.icon }}</span>
          <span class="font-label flex-1">{{ item.label }}</span>
          <span
            v-if="item.badge > 0"
            class="min-w-[20px] h-5 px-1.5 rounded-full bg-white/20 text-[10px] font-bold flex items-center justify-center"
          >{{ item.badge > 99 ? '99+' : item.badge }}</span>
        </router-link>
      </nav>
      <div class="mt-auto px-6 pt-6 border-t border-white/10">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30">
            <span class="material-symbols-outlined text-primary text-sm">person</span>
          </div>
          <div>
            <p class="text-xs font-bold text-white">{{ userStore.worker?.name || '管理员' }}</p>
            <p class="text-[10px] text-white/40">{{ userStore.worker?.role_label || '超级管理员' }}</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- TopNavBar -->
    <header v-show="!dashboardStore.presentationMode" class="h-16 fixed top-0 right-0 w-[calc(100%-240px)] bg-surface/80 backdrop-blur-md flex justify-between items-center px-8 z-40 border-b border-outline-variant/30">
      <div class="flex items-center gap-4">
        <h2 class="font-headline font-semibold text-lg text-on-surface">{{ currentPageName }}</h2>
        <div v-if="userStore.communities.length > 1" class="community-switcher">
          <select
            :value="userStore.currentCommunityId"
            class="bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-1.5 text-sm text-on-surface focus:ring-1 focus:ring-primary/30 focus:outline-none cursor-pointer transition-all"
            @change="handleSwitchCommunity($event.target.value)"
          >
            <option
              v-for="c in userStore.communities"
              :key="c.community_id"
              :value="c.community_id"
            >{{ c.community_name }}</option>
          </select>
        </div>
      </div>
      <div class="flex items-center gap-4 text-on-surface-variant">
        <button class="hover:text-primary transition-colors" @click="userStore.logout()">
          <span class="material-symbols-outlined">logout</span>
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main :class="[
      'h-screen overflow-y-auto custom-scrollbar bg-surface transition-all duration-300',
      dashboardStore.presentationMode ? 'ml-0 pt-0' : 'ml-60 pt-16'
    ]">
      <div :class="dashboardStore.presentationMode ? 'p-6' : 'p-8 max-w-[1400px] mx-auto'">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useDashboardStore } from '@/stores/dashboard'
import { useEldersStore } from '@/stores/elders'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const dashboardStore = useDashboardStore()
const eldersStore = useEldersStore()

onMounted(() => {
  userStore.loadCommunities()
})

async function handleSwitchCommunity(communityId) {
  if (communityId === userStore.currentCommunityId) return
  try {
    await userStore.switchCommunity(communityId)
    dashboardStore.load()
    eldersStore.load()
    if (route.path !== '/dashboard') {
      router.push('/dashboard')
    }
  } catch (e) {
    // handled by request interceptor
  }
}

const navItems = computed(() => [
  { path: '/dashboard', label: '看板', icon: 'dashboard' },
  { path: '/elders', label: '老人档案', icon: 'groups' },
  { path: '/canteen', label: '食堂管理', icon: 'restaurant' },
  { path: '/events', label: '事件中心', icon: 'notifications_active', badge: dashboardStore.data?.pending_events || 0 },
  { path: '/agent', label: 'AI 助手', icon: 'smart_toy' },
  { path: '/volunteers', label: '邻里帮', icon: 'volunteer_activism' },
])

const pageNameMap = {
  '/dashboard': '看板 / 概览',
  '/elders': '老人档案',
  '/canteen': '食堂管理',
  '/events': '事件中心',
  '/agent': 'AI 助手',
  '/volunteers': '邻里帮',
}

const currentPageName = computed(() => {
  return pageNameMap[route.path] || (route.path.startsWith('/elders/') ? '老人详情' : '看板')
})
</script>

<style scoped>
.page-fade-enter-active {
  transition: opacity 250ms cubic-bezier(0.16, 1, 0.3, 1), transform 250ms cubic-bezier(0.16, 1, 0.3, 1);
}
.page-fade-leave-active {
  transition: opacity 150ms cubic-bezier(0.16, 1, 0.3, 1);
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
}
</style>
