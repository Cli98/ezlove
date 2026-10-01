<template>
  <AppPanel class="result-card">
    <h2>本次解析结果</h2>
    <p>{{ mealLabel }} · 出席 {{ present.length }} 人 · 未到 {{ absent.length }} 人</p>
    <div class="attendance-row absent-row">
      <strong><span class="material-symbols-outlined">person</span>未到食堂</strong>
      <div>
        <span v-for="person in absent" :key="person.elder_id || person.elder_name" class="person-tag">{{ person.elder_name }}<b v-if="person.care_level" :class="`level-${person.care_level}`">{{ person.care_level }}类</b></span>
        <em v-if="!absent.length">无</em>
      </div>
    </div>
    <div class="attendance-row present-row">
      <strong><span class="material-symbols-outlined">person</span>已到食堂</strong>
      <div>
        <span v-for="person in present" :key="person.elder_id || person.elder_name" class="person-tag">{{ person.elder_name }}</span>
        <em v-if="!present.length">无</em>
      </div>
    </div>
  </AppPanel>
</template>

<script setup>
import { computed } from 'vue'
import AppPanel from '@/components/AppPanel.vue'

const props = defineProps({ result: { type: Object, default: () => ({}) } })
const attendees = computed(() => props.result?.attendees || [])
const present = computed(() => attendees.value.filter(person => person.present === true))
const absent = computed(() => attendees.value.filter(person => person.present === false))
const mealLabel = computed(() => ({ breakfast: '早餐', lunch: '午餐', dinner: '晚餐' }[props.result?.meal_type] || '本餐次'))
</script>

<style scoped>
.result-card { padding: 15px 20px; overflow: auto; }.result-card h2 { margin: 0; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }.result-card > p { margin: 7px 0 14px; color: #3e5270; font-size: 12px; }.attendance-row { display: grid; grid-template-columns: 105px 1fr; align-items: center; gap: 8px; margin-top: 8px; }.attendance-row > strong { display: flex; align-items: center; gap: 8px; color: #243249; font-size: 12px; white-space: nowrap; }.attendance-row > strong span { color: #cf553d; font-size: 21px; }.present-row > strong span { color: #4e8a6e; }.attendance-row > div { display: flex; min-width: 0; flex-wrap: wrap; gap: 7px; }.person-tag { display: inline-flex; min-height: 30px; align-items: center; gap: 8px; padding: 0 12px; border-radius: 5px; color: #34445b; background: #f6f7f5; font-size: 11px; }.person-tag b { padding: 3px 7px; border-radius: 999px; color: #a46f1e; background: #fbf0dc; font-size: 10px; }.person-tag b.level-A { color: #c34d39; background: #fae9e3; }.attendance-row em { color: #9a948e; font-size: 11px; font-style: normal; }
</style>
