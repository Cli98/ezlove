<template>
  <section class="panel care-overview">
    <div class="panel__head">
      <h2>片区关怀概览</h2>
      <button @click="$emit('all')">查看全部 <DashboardIcon name="chevron-right" /></button>
    </div>
    <div class="areas">
      <article v-for="area in areas" :key="area.name">
        <b>{{ area.name }}</b>
        <span>{{ area.count }} 位老人</span>
        <div class="area-bar"><i :style="{ width: `${area.rate}%` }" :class="area.rate < 70 ? 'warm' : ''"></i></div>
        <em>{{ area.rate }}%</em>
      </article>
      <p v-if="!areas.length" class="side-empty">暂无片区数据</p>
    </div>
    <img class="area-art" src="@/assets/dashboard-composite/area-community-art.png" alt="社区楼宇水彩插画" />
  </section>
</template>

<script setup>
import DashboardIcon from '@/components/DashboardIcon.vue'

defineEmits(['all'])
defineProps({ areas: { type: Array, default: () => [] } })
</script>

<style scoped>
.panel { position: relative; min-height: 0; overflow: hidden; padding-bottom: 73px; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.78); box-shadow: 0 2px 8px rgba(57,45,36,.025); }
.panel__head { display: flex; min-height: 55px; align-items: center; justify-content: space-between; padding: 12px 17px 8px; }
.panel__head h2 { margin: 0; color: #272624; font: 700 20px 'Songti SC', 'STSong', serif; }
.panel__head button { display: flex; align-items: center; gap: 5px; padding: 0; border: 0; color: #716e6a; background: transparent; font-size: 13px; cursor: pointer; }
.panel__head button :deep(.dashboard-icon) { font-size: 16px; }
.areas { max-height: calc(100% - 55px); overflow-y: auto; padding: 0 19px 73px; scrollbar-width: thin; }
.areas article { display: grid; grid-template-columns: 78px 1fr 100px 33px; gap: 8px; align-items: center; padding: 9px 0; }
.areas b { color: #303033; font-size: 14px; }.areas span { color: #555d6b; font-size: 13px; }
.area-bar { height: 10px; overflow: hidden; border-radius: 20px; background: #e7e5e2; }
.area-bar i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #739986, #557b69); }
.area-bar i.warm { background: linear-gradient(90deg, #d89338, #c97822); }
.areas em { color: #525a68; font-size: 13px; font-style: normal; text-align: right; }
.side-empty { margin: 34px 0 0; color: #91867c; text-align: center; font-size: 14px; }
.area-art { position: absolute; right: 0; bottom: 0; width: 100%; height: auto; pointer-events: none; }
@media (max-width: 1180px) { .areas article { grid-template-columns: 68px 1fr 75px 30px; gap: 6px; } }
@media (max-width: 1050px) { .panel { min-height: 281px; }.areas { max-height: none; overflow: visible; } }
</style>
