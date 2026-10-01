<template>
  <div class="app-layout">
    <AppSidebar v-show="!dashboardStore.presentationMode" :items="navItems" />

    <!-- TopNavBar -->
    <header v-show="!dashboardStore.presentationMode && !isImmersivePage" class="app-header h-16 fixed top-0 right-0 bg-surface/80 backdrop-blur-md flex justify-between items-center px-8 z-40 border-b border-outline-variant/30">
      <div class="flex items-center gap-4">
        <h2 class="font-headline font-semibold text-lg text-on-surface">{{ currentPageName }}</h2>
        <div v-if="userStore.communities.length > 1" class="community-switcher">
          <InlineSelect
            :model-value="userStore.currentCommunityId"
            :options="communityOptions"
            class="bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-1.5 text-sm text-on-surface focus:ring-1 focus:ring-primary/30 focus:outline-none cursor-pointer transition-all"
            @change="handleSwitchCommunity"
          />
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
      'app-main-frame custom-scrollbar bg-surface transition-all duration-300',
      dashboardStore.presentationMode ? 'ml-0 pt-0 overflow-y-auto' : isImmersivePage ? 'app-main app-main--dashboard overflow-y-auto' : 'app-main pt-16 overflow-y-auto'
    ]">
      <div :class="dashboardStore.presentationMode ? 'p-6' : isImmersivePage ? 'dashboard-shell' : 'p-8 max-w-[1400px] mx-auto'">
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
import AppSidebar from '@/components/AppSidebar.vue'
import InlineSelect from '@/components/InlineSelect.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const dashboardStore = useDashboardStore()
const eldersStore = useEldersStore()
const isImmersivePage = computed(() => route.path === '/dashboard' || route.path.startsWith('/elders') || route.path === '/canteen' || route.path === '/events' || route.path === '/volunteers' || route.path === '/agent')
const communityOptions = computed(() => userStore.communities.map(community => ({ value: community.community_id, label: community.community_name })))
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
  { path: '/dashboard', label: '今日工作台', icon: 'home' },
  { path: '/elders', label: '老人档案', icon: 'archive' },
  { path: '/canteen', label: '食堂记录', icon: 'bowl' },
  { path: '/events', label: '关怀事件', icon: 'heart', badge: dashboardStore.data?.pending_events || 0 },
  { path: '/volunteers', label: '邻里帮', icon: 'people' },
  { path: '/agent', label: 'AI 助手', icon: 'sparkle' },
])

const pageNameMap = {
  '/dashboard': '看板 / 概览',
  '/elders': '老人档案',
  '/canteen': '食堂记录',
  '/events': '关怀事件',
  '/agent': 'AI 助手',
  '/volunteers': '邻里帮',
}

const currentPageName = computed(() => {
  return pageNameMap[route.path] || (route.path.startsWith('/elders/') ? '老人详情' : '看板')
})
</script>

<style scoped>
.app-layout {
  --sidebar-width: clamp(170px, 13vw, 200px);
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #fbf8f4;
}
.app-header { width: calc(100% - var(--sidebar-width)); }
.app-main-frame { height: 100%; }
.app-main { margin-left: var(--sidebar-width); }
.app-main--dashboard { background: radial-gradient(circle at 18% 8%, rgba(218, 177, 142, .07), transparent 28%), #fbf8f4; }
.dashboard-shell { height: 100%; padding: 12px 28px 18px 24px; }
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
