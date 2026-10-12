<template>
  <aside class="app-sidebar">
    <div class="sidebar-brand">
      <img src="@/assets/dashboard-composite/logo-mark.png" alt="" />
      <strong>易挂念</strong>
    </div>
    <nav class="sidebar-nav">
      <router-link
        v-for="item in items"
        :key="item.path"
        :to="item.path"
        :class="[
          'sidebar-link',
          route.path === item.path || (item.path !== '/dashboard' && route.path.startsWith(item.path))
            ? 'sidebar-link--active'
            : ''
        ]"
      >
        <DashboardIcon :name="item.icon" />
        <span>{{ item.label }}</span>
        <span v-if="item.badge > 0" class="sidebar-badge">{{ item.badge > 99 ? '99+' : item.badge }}</span>
      </router-link>
    </nav>
    <img class="sidebar-care" src="@/assets/dashboard-composite/sidebar-care-art-brown.png" alt="相互陪伴的老人插画" />
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import DashboardIcon from '@/components/DashboardIcon.vue'

defineProps({ items: { type: Array, default: () => [] } })
const route = useRoute()
</script>

<style scoped>
.app-sidebar { position: fixed; inset: 0 auto 0 0; z-index: 50; display: flex; width: var(--sidebar-width); height: 100%; flex-direction: column; overflow: hidden; color: #fff; background: linear-gradient(180deg,#302c27 0%,#292620 100%); box-shadow: 8px 0 28px rgba(37,31,26,.1); }
.sidebar-brand { position: relative; z-index: 1; display: flex; height: 92px; flex: none; align-items: center; gap: 10px; padding: 0 22px; border-bottom: 1px solid rgba(255,255,255,.06); }
.sidebar-brand img { width: 38px; height: 42px; object-fit: contain; }
.sidebar-brand strong { color: #fff; font: 700 20px/1 'Songti SC','STSong',serif; letter-spacing: .08em; white-space: nowrap; }
.sidebar-nav { position: relative; z-index: 1; display: grid; gap: 4px; padding: 10px; }
.sidebar-link { position: relative; display: flex; height: 50px; align-items: center; gap: 12px; padding: 0 14px; border-radius: 10px; color: rgba(255,255,255,.72); font-size: 14px; text-decoration: none; transition: color .2s, background .2s; }
.sidebar-link > * { position: relative; z-index: 2; }
.sidebar-link > span:first-of-type { display: inline-block; min-width: 0; flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.sidebar-link :deep(.dashboard-icon) { flex: none; font-size: 22px; opacity: .88; }
.sidebar-link:hover { color: #fff; background: rgba(255,255,255,.055); }
.sidebar-link--active { color: #fff; background: linear-gradient(90deg,rgba(208,111,78,.28),rgba(255,255,255,.075)); box-shadow: inset 0 0 0 1px rgba(255,255,255,.035); }
.sidebar-link--active::before { content: ''; position: absolute; top: 12px; bottom: 12px; left: 0; width: 3px; border-radius: 0 3px 3px 0; background: #e08b68; box-shadow: 0 0 10px rgba(224,139,104,.35); }
.sidebar-badge { display: flex; min-width: 22px; height: 22px; flex: none; align-items: center; justify-content: center; padding: 0 6px; border-radius: 999px; color: #fff; background: rgba(224,139,104,.7); font-size: 10px; font-weight: 700; }
.sidebar-care { position: absolute; z-index: 0; bottom: 0; left: 0; display: block; width: 100%; height: auto; opacity: .78; filter: saturate(.82); pointer-events: none; }
</style>
