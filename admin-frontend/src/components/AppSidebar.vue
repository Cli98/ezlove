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
.app-sidebar { position: fixed; inset: 0 auto 0 0; z-index: 50; display: flex; width: var(--sidebar-width); height: 100%; flex-direction: column; overflow: hidden; color: #fff; background: #302c27; box-shadow: 10px 0 36px rgba(37,31,26,.08); }
.sidebar-brand { position: relative; z-index: 1; display: flex; height: clamp(84px,11.8vh,116px); align-items: center; gap: 8px; padding: 10px 20px 6px; }
.sidebar-brand img { width: 40px; height: 44px; object-fit: contain; }
.sidebar-brand strong { color: #fff; font: 700 21px/1 'Songti SC','STSong',serif; letter-spacing: .08em; white-space: nowrap; }
.sidebar-nav { position: relative; z-index: 1; display: grid; gap: clamp(0px,calc(2.5vh - 19.5px),6px); }
.sidebar-link { position: relative; display: flex; height: clamp(46px,6.4vh,62px); align-items: center; gap: 15px; margin-right: 6px; padding: 0 28px; border-radius: 0 5px 5px 0; color: rgba(255,255,255,.82); font-size: 14.5px; transition: color .2s; }
.sidebar-link > * { position: relative; z-index: 2; }
.sidebar-link > span:first-of-type { display: inline-block; transform: scaleX(.92); transform-origin: left center; }
.sidebar-link :deep(.dashboard-icon) { font-size: 23px; }
.sidebar-link::after { content: ''; position: absolute; z-index: 0; inset: 0 0 0 6px; border-radius: 5px; background: rgba(255,255,255,.05); opacity: 0; transition: opacity .2s; pointer-events: none; }
.sidebar-link:hover { color: #fff; background: transparent; }.sidebar-link:hover::after { opacity: 1; }
.sidebar-link--active { isolation: isolate; color: #fff; background: transparent; box-shadow: none; }.sidebar-link--active::after { background: rgba(111,85,72,.68); opacity: 1; }
.sidebar-link--active::before { content: ''; position: absolute; z-index: 1; top: clamp(3px,.5vh,5px); bottom: clamp(3px,.5vh,5px); left: 0; width: 6px; background: #d98766; box-shadow: 0 0 10px rgba(217,135,102,.3); }
.sidebar-badge { display: flex; min-width: 20px; height: 20px; align-items: center; justify-content: center; padding: 0 6px; border-radius: 999px; background: rgba(255,255,255,.2); font-size: 10px; font-weight: 700; }
.sidebar-care { position: absolute; z-index: 0; bottom: 0; left: 0; display: block; width: 100%; height: auto; pointer-events: none; }
</style>
