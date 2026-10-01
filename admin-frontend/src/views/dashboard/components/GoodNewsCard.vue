<template>
  <section class="panel good-news">
    <div class="panel__head">
      <h2>最近的好消息</h2>
      <button @click="$emit('all')">查看全部 <DashboardIcon name="chevron-right" /></button>
    </div>
    <div class="good-news__list">
      <article v-for="item in items" :key="item.text">
        <DashboardIcon :name="item.icon" :class="item.tone" />
        <p>{{ item.text }}</p>
        <time>{{ item.time }}</time>
      </article>
    </div>
  </section>
</template>

<script setup>
import DashboardIcon from '@/components/DashboardIcon.vue'

defineEmits(['all'])
defineProps({ items: { type: Array, default: () => [] } })
</script>

<style scoped>
.panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; padding-bottom: 14px; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.78); box-shadow: 0 2px 8px rgba(57,45,36,.025); }
.panel__head { display: flex; min-height: 55px; align-items: center; justify-content: space-between; padding: 12px 17px 8px; }
.panel__head h2 { margin: 0; color: #272624; font: 700 20px 'Songti SC', 'STSong', serif; }
.panel__head button { display: flex; align-items: center; gap: 5px; padding: 0; border: 0; color: #716e6a; background: transparent; font-size: 13px; cursor: pointer; }
.panel__head button :deep(.dashboard-icon) { font-size: 16px; }
.good-news__list { min-height: 0; overflow-y: auto; scrollbar-width: thin; }
.good-news article { display: grid; grid-template-columns: 28px minmax(0,1fr) auto; align-items: center; gap: 8px; padding: 8px 18px; }
.good-news article > :deep(.dashboard-icon) { font-size: 25px; }
.good-news p { margin: 0; overflow: hidden; color: #3e3c3a; font-size: 14px; white-space: nowrap; text-overflow: ellipsis; }
.good-news time { color: #898b90; font-size: 12px; }.heart { color: #cf654b; }.food { color: #cb8433; }.walk { color: #56826a; }
@media (max-width: 1050px) { .good-news__list { overflow: visible; } }
</style>
