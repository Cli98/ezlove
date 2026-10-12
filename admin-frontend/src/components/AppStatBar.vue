<template>
  <section class="app-stat-bar focus-gradient-surface">
    <article v-for="stat in stats" :key="stat.label" class="app-stat-bar__item">
      <DashboardIcon :name="stat.icon" :class="`app-stat-bar__icon--${stat.tone}`" />
      <strong :class="`app-stat-bar__value--${stat.tone}`">{{ stat.value }}</strong>
      <div><b>{{ stat.label }}</b><small>{{ stat.detail }}</small></div>
    </article>
  </section>
</template>

<script setup>
import DashboardIcon from '@/components/DashboardIcon.vue'

defineProps({ stats: { type: Array, default: () => [] } })
</script>

<style scoped>
.app-stat-bar { display: grid; grid-template-columns: repeat(3, 1fr); margin: 0 0 14px; padding: 7px 18px; border: 1px solid rgba(226,208,194,.68); border-radius: 12px; }
.app-stat-bar__item { position: relative; z-index: 1; display: flex; min-width: 0; min-height: 78px; align-items: center; gap: 20px; padding: 4px 34px; }
.app-stat-bar__item:first-child { padding-left: 40px; }
.app-stat-bar__item:not(:last-child)::after { content: ''; position: absolute; top: 50%; right: 0; width: 1px; height: 56px; background: rgba(220,185,160,.56); transform: translateY(-50%); }
.app-stat-bar__item > :deep(.dashboard-icon) { font-size: 36px; transform: translateY(4px); }
.app-stat-bar__item strong { font-family: 'Bodoni 72', Didot, 'Times New Roman', serif; font-size: 44px; font-weight: 700; font-variant-numeric: lining-nums tabular-nums; letter-spacing: -.045em; line-height: .9; transform: translateY(-4px); }
.app-stat-bar__item div { display: grid; gap: 5px; transform: translateY(4px); }
.app-stat-bar__item b { color: #2d2926; font-size: 14.5px; line-height: 1.2; }
.app-stat-bar__item small { color: #8d8780; font-size: 10.5px; line-height: 1.25; white-space: nowrap; }
.app-stat-bar__icon--terracotta, .app-stat-bar__value--terracotta { color: #c75a3d; }
.app-stat-bar__icon--amber, .app-stat-bar__value--amber { color: #d68f30; }
.app-stat-bar__icon--sage, .app-stat-bar__value--sage { color: #56826a; }
@media (max-width: 1180px) { .app-stat-bar__item { gap: 10px; padding-inline: 16px; }.app-stat-bar__item:first-child { padding-left: 16px; } }
@media (max-width: 840px) { .app-stat-bar { grid-template-columns: 1fr; }.app-stat-bar__item { padding: 10px 12px; border-bottom: 1px solid #ead6c7; }.app-stat-bar__item:first-child { padding-left: 12px; }.app-stat-bar__item:not(:last-child)::after { display: none; }.app-stat-bar__item:last-child { border-bottom: 0; } }
</style>
