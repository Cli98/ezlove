<template>
  <section class="activity-card">
    <header>
      <h2>今天的活动</h2>
      <div class="date-picker">
        <button aria-label="前一天" @click="shiftDay(-1)"><span class="material-symbols-outlined">chevron_left</span></button>
        <span>{{ dateLabel }}</span>
        <button :disabled="isToday" aria-label="后一天" @click="shiftDay(1)"><span class="material-symbols-outlined">chevron_right</span></button>
      </div>
    </header>
    <div v-if="loading" class="activity-state">正在整理活动记录…</div>
    <template v-else>
      <div class="activity-track">
        <div class="time-ruler">
          <span v-for="tick in timeTicks" :key="tick"><b>{{ tick }}</b><i></i></span>
        </div>
        <div class="activity-events">
          <article v-for="item in trackItems" :key="item.id" :class="`event--${toneOf(item)}`">
            <i class="event-node"></i>
            <span class="activity-icon material-symbols-outlined">{{ iconOf(item.type, item.label) }}</span>
            <time>{{ timeOf(item.time) }}</time>
            <b>{{ item.label }}</b>
          </article>
          <article v-if="trackItems.length < 5" class="activity-empty">
            <i class="event-node"></i><span class="activity-icon"></span><time></time><b>暂无新动态</b>
          </article>
        </div>
      </div>
      <div class="recent-title">最近活动</div>
      <div class="recent-table">
        <div class="recent-head"><span>时间</span><span>事件</span><span>来源</span></div>
        <div v-for="(item,index) in recentItems" :key="`row-${item.id}`" :class="['recent-row', { first: index === 0, last: index === recentItems.length - 1 }]">
          <time><i class="timeline-dot"></i><span>{{ dayOf(item.time) }}</span><span>{{ timeOf(item.time) }}</span></time>
          <span><i class="material-symbols-outlined">{{ iconOf(item.type, item.label) }}</i>{{ item.label }}</span>
          <em>{{ item.source || sourceOf(item.type) }}</em>
        </div>
        <div v-if="!items.length" class="recent-empty">该日暂无活动记录</div>
      </div>
      <button class="all-activity" @click="$emit('all')">查看全部活动记录 <span>›</span></button>
    </template>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { getElderDayActivity } from '@/api/community'

defineEmits(['all'])
const props = defineProps({ elderId: { type: String, required: true }, initialItems: { type: Array, default: () => [] }, mock: Boolean })
const currentDate = ref(new Date().toISOString().slice(0,10))
const items = ref([])
const loading = ref(false)
const isToday = computed(() => currentDate.value === new Date().toISOString().slice(0,10))
const dateLabel = computed(() => { const d = new Date(`${currentDate.value}T00:00:00`); return `${d.getMonth()+1}月${d.getDate()}日${isToday.value ? '（今天）' : ''}` })
const trackItems = computed(() => [...items.value].sort((a,b) => new Date(a.time)-new Date(b.time)).slice(0,5))
const recentItems = computed(() => items.value.slice(0,4))
const timeTicks = ['05:00','08:00','11:00','14:00','17:00','20:00','23:00']

function shiftDay(offset) { const date = new Date(`${currentDate.value}T00:00:00`); date.setDate(date.getDate()+offset); currentDate.value = date.toISOString().slice(0,10) }
function timeOf(value) { const d = new Date(value); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}` }
function dayOf(value) { const d = new Date(value); return `${d.getMonth()+1}月${d.getDate()}日` }
function iconOf(type, label = '') { if (label.includes('起床')) return 'bed'; return { canteen_present:'restaurant', canteen_absent:'no_meals', view:'favorite', event:'directions_walk', alert:'error' }[type] || 'schedule' }
function sourceOf(type) { return type?.startsWith('canteen') ? '食堂' : type === 'view' ? '小程序' : type === 'alert' ? '关怀事件' : '社区' }
function toneOf(item) { return ['warning','critical'].includes(item.severity) || item.type === 'alert' ? 'danger' : 'normal' }

async function load() {
  if (isToday.value) { items.value = props.initialItems; return }
  if (props.mock) { items.value = []; return }
  loading.value = true
  try {
    const data = await getElderDayActivity(props.elderId, currentDate.value)
    items.value = (data.signals || []).map((item,index) => ({ ...item, id:`${currentDate.value}-${index}`, time:new Date(`${currentDate.value}T${String(item.hour).padStart(2,'0')}:${String(item.minute || 0).padStart(2,'0')}:00`).toISOString() }))
  } catch { items.value = [] } finally { loading.value = false }
}

watch([currentDate, () => props.initialItems], load, { immediate:true })
</script>

<style scoped>
.activity-card { display: flex; min-height: 0; flex-direction: column; overflow: hidden; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.8); }.activity-card header { display: flex; min-height: 62px; align-items: center; justify-content: space-between; padding: 12px 18px 8px; }.activity-card h2, .recent-title { margin: 0; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }.date-picker { display: grid; width: 172px; height: 32px; grid-template-columns: 34px 1fr 34px; align-items: stretch; overflow: hidden; border: 1px solid #e2dcd5; border-radius: 7px; background: #fff; }.date-picker button { display: grid; width: 34px; height: 100%; padding: 0; place-items: center; border: 0; color: #43516a; background: transparent; cursor: pointer; }.date-picker button .material-symbols-outlined { display: block; font-size: 20px; line-height: 1; }.date-picker button:disabled { opacity: .35; }.date-picker > span { display: grid; min-width: 0; place-items: center; color: #536076; font-size: 12px; line-height: 1; text-align: center; }
.activity-track { position: relative; min-height: 156px; padding: 7px 18px 16px; }.time-ruler { position: relative; display: grid; grid-template-columns: repeat(7,1fr); height: 45px; color: #526078; }.time-ruler::after { content: ''; position: absolute; right: 0; bottom: 9px; left: 0; height: 2px; background: #ded8d1; }.time-ruler span { position: relative; display: grid; justify-items: center; font-size: 10px; font-weight: 400; }.time-ruler span:first-child { justify-items: start; }.time-ruler span:last-child { justify-items: end; }.time-ruler b { font-weight: 500; }.time-ruler i { position: absolute; z-index: 1; bottom: 5px; left: 50%; width: 1px; height: 9px; background: #d0c9c2; transform: translateX(-50%); }.time-ruler span:first-child i { left: 8px; }.time-ruler span:last-child i { right: 8px; left: auto; }.activity-events { position: relative; display: grid; grid-template-columns: repeat(5,1fr); margin-top: -10px; }.activity-events::before { content: ''; position: absolute; top: 37px; right: 10%; left: 70%; border-top: 1px dashed #c5cdd5; }.activity-events article { position: relative; z-index: 2; display: grid; grid-template-rows: 12px 38px 16px 18px; justify-items: center; color: #3f4d63; }.event-node { width: 7px; height: 7px; border-radius: 50%; background: #5e8a75; }.activity-events article::before { content: ''; position: absolute; top: -1px; left: 50%; width: 1px; height: 13px; background: #5e8a75; transform: translateX(-50%); }.activity-icon { display: grid; box-sizing: border-box; width: 35px; height: 35px; place-items: center; border: 2px solid #608d79; border-radius: 50%; color: #507c67; background: #fff; font-size: 21px; }.activity-events time { color: #334158; font-size: 11px; font-weight: 800; }.activity-events b { font-size: 12px; }.event--danger .event-node, .event--danger::before { background: #dc4f34; }.event--danger .activity-icon { color: #dc4f34; border-color: #dc4f34; }.event--danger time, .event--danger b { color: #dc4f34; }.activity-empty { color: #8a919b!important; }.activity-empty::before { background: transparent!important; }.activity-empty .event-node { background: #5e8a75; }.activity-empty .activity-icon { border: 1px dashed #9ea8b7; }
.activity-events { margin-top: -14px; }
.activity-events::before { top: 29px; }
.activity-events article { --event-color: #5e8a75; }
.activity-events article::before { z-index: 0; top: 3px; height: 27px; background: var(--event-color); }
.event-node { position: relative; z-index: 2; background: var(--event-color); }
.activity-icon { position: relative; z-index: 1; color: var(--event-color); border-color: var(--event-color); }
.event--danger { --event-color: #dc4f34!important; }
.activity-empty::before { display: none; }
.activity-empty .event-node { visibility: hidden; }
.recent-title { margin: 0 18px; padding-top: 12px; border-top: 1px solid #eee8e2; }.recent-table { min-height: 0; margin: 10px 18px 0; overflow-y: auto; }.recent-head, .recent-row { display: grid; grid-template-columns: 180px 1fr 100px; align-items: center; }.recent-head { padding: 9px 12px; border-radius: 7px; color: #657083; background: linear-gradient(90deg,#faf1e9,#fbf7f2); font-size: 12px; }.recent-head span:first-child { padding-left: 28px; }.recent-row { position: relative; min-height: 38px; padding: 0 12px; color: #536077; font-size: 12px; }.recent-row::after { content: ''; position: absolute; right: 0; bottom: 0; left: 40px; height: 1px; background: #eee9e4; }.recent-row time { position: relative; display: grid; align-self: stretch; grid-template-columns: 74px auto; align-items: center; padding-left: 28px; font-style: normal; }.recent-row time::before { content: ''; position: absolute; top: 0; bottom: 0; left: 8px; width: 1px; background: rgba(216,90,66,.3); transform: translateX(-50%); }.recent-row.first time::before { top: 50%; }.recent-row.last time::before { bottom: 50%; }.recent-row .timeline-dot { position: absolute; z-index: 1; top: 50%; left: 4px; box-sizing: border-box; width: 8px; height: 8px; border: 2px solid #d85a42; border-radius: 50%; background: #fff; transform: translateY(-50%); }.recent-row > span { display: flex; align-items: center; gap: 9px; color: #445167; }.recent-row > span i { color: #56826a; font-size: 20px; }.recent-row em { font-style: normal; }.recent-empty, .activity-state { display: grid; min-height: 100px; place-items: center; color: #91867c; font-size: 13px; }.all-activity { display: flex; min-height: 42px; align-items: center; justify-content: space-between; margin: auto 18px 14px; padding: 0 14px; border: 0; border-radius: 7px; color: #566176; background: linear-gradient(90deg,#faf1e9,#fbf7f2); font-size: 12px; cursor: pointer; }
</style>
