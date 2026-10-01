<template>
  <section class="panel priority-panel">
    <div class="panel__head"><h2>优先处理</h2><button @click="$emit('all')"><DashboardIcon name="filter" /> 全部 <DashboardIcon name="chevron-down" /></button></div>
    <div class="priority-table">
      <div class="priority-table__head"><span>老人信息</span><span>关怀提示</span><span>最后动态</span><span>信息来源</span><span>操作</span></div>
      <div class="priority-table__body">
        <div v-if="loading" class="priority-empty">正在整理今日关怀重点…</div>
        <div v-else-if="!items.length" class="priority-empty"><DashboardIcon name="heart" />今天的重点已处理完毕</div>
        <template v-else>
          <article v-for="item in items" :key="item.id" class="priority-row">
            <div class="elder"><img class="elder__avatar" :src="item.avatar" :alt="item.name" /><div><b>{{ item.name }}</b><small>{{ item.address || '社区居民' }}</small></div></div>
            <div class="care-tip"><span :class="`tag tag--${item.careLevel}`">{{ item.careLevel }}类</span><p>{{ item.message }}</p></div>
            <time>{{ item.time }}</time>
            <div class="source"><DashboardIcon :name="item.icon" :class="`source--${item.tone}`" /><div>{{ item.source }}<small>{{ item.sourceDetail }}</small></div></div>
            <button class="view-button" @click="$emit('view', item.elderId || item.id)">查看档案</button>
          </article>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup>
import DashboardIcon from '@/components/DashboardIcon.vue'

defineEmits(['all', 'view'])
defineProps({ items: { type: Array, default: () => [] }, loading: Boolean })
</script>

<style scoped>
.panel { border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.78); box-shadow: 0 2px 8px rgba(57,45,36,.025); }.priority-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }.panel__head { display: flex; min-height: 60px; align-items: center; justify-content: space-between; padding: 9px 18px 6px; }.panel__head h2 { margin: 0; color: #272624; font: 700 21px 'Songti SC', 'STSong', serif; }.panel__head button { display: flex; align-items: center; gap: 8px; padding: 5px; border: 0; color: #626975; background: transparent; font-size: 13px; cursor: pointer; }.panel__head button :deep(.dashboard-icon) { font-size: 18px; }
.priority-table { display: flex; min-height: 0; flex: 1; flex-direction: column; padding: 0 14px 14px; }.priority-table__body { display: flex; min-height: 0; flex: 1; flex-direction: column; overflow-y: auto; scrollbar-width: thin; }.priority-table__head, .priority-row { display: grid; grid-template-columns: 1.17fr 1.5fr .76fr 1.14fr .52fr; align-items: center; column-gap: 12px; }.priority-table__head { flex: none; padding: 12px; color: #6e6e73; background: linear-gradient(90deg, #f7f5f2, #faf9f7); border-radius: 8px; font-size: 13px; font-weight: 800; }.priority-row { min-height: 79px; padding: 9px 12px; border-bottom: 1px solid #eee9e4; }.priority-row:last-child { border-bottom: 0; }.elder, .source { display: flex; align-items: center; gap: 10px; min-width: 0; }.elder__avatar { width: 45px; height: 48px; flex: 0 0 auto; object-fit: cover; border-radius: 8px; }.elder b, .source div { overflow: hidden; color: #292727; font-size: 14px; }.elder small, .source small { display: block; overflow: hidden; margin-top: 3px; color: #88827d; font-size: 12px; white-space: nowrap; text-overflow: ellipsis; }.care-tip { display: flex; align-items: center; gap: 9px; }.care-tip p { margin: 0; color: #49443f; font-size: 13px; line-height: 1.5; }.tag { flex: none; padding: 5px 8px; border-radius: 16px; font-size: 12px; }.tag--A { color: #c2533b; background: #fae9e1; }.tag--B { color: #56826a; background: #e9f2eb; }.source > :deep(.dashboard-icon) { font-size: 26px; }.source--terracotta { color: #ce6448; }.source--sage { color: #56826a; }.source--amber { color: #d68f30; }.priority-row time { color: #747a88; font-size: 12px; }.view-button { padding: 0; border: 0; color: #c44d3e; background: transparent; font-weight: 700; font-size: 12px; white-space: nowrap; cursor: pointer; }
.priority-empty { display: grid; min-height: 0; flex: 1; place-items: center; align-content: center; gap: 12px; color: #91867c; font-size: 16px; }.priority-empty :deep(.dashboard-icon) { color: #c44d3e; font-size: 25px; }
@media (max-width: 1020px) { .priority-table__head, .priority-row { grid-template-columns: 1.2fr 1.7fr .9fr; }.priority-table__head > :nth-child(3), .priority-table__head > :nth-child(4), .priority-row > time, .priority-row > .source { display: none; } }
</style>
