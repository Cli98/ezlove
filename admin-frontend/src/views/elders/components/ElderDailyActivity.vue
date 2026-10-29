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
        <div v-if="trackNodes.length" class="activity-events">
          <article
            v-for="node in trackNodes"
            :key="node.id"
            :class="['event-pin', node.danger ? 'event--danger' : 'event--normal']"
            :style="{ left: `${node.left}%` }"
          >
            <i class="event-node"></i>
            <span class="activity-icon material-symbols-outlined">
              {{ iconOf(node.type, node.label) }}
              <em v-if="node.count > 1" class="event-count">{{ node.count }}</em>
            </span>
            <time>{{ timeOf(node.time) }}</time>
            <b>{{ node.label }}</b>
          </article>
        </div>
        <div v-else class="activity-track-empty">暂无新动态</div>
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
const props = defineProps({ elderId: { type: String, required: true }, initialItems: { type: Array, default: () => [] } })
const currentDate = ref(new Date().toISOString().slice(0,10))
const items = ref([])
const loading = ref(false)
const isToday = computed(() => currentDate.value === new Date().toISOString().slice(0,10))
const dateLabel = computed(() => { const d = new Date(`${currentDate.value}T00:00:00`); return `${d.getMonth()+1}月${d.getDate()}日${isToday.value ? '（今天）' : ''}` })
const recentItems = computed(() => items.value.slice(0, 8))
const DAY_START = 5 * 60
const DAY_END = 23 * 60
// 时间轴按真实时刻定位：同一小时、或相距不足 75 分钟的事件合并成一个节点，避免标签叠在一起。
const trackNodes = computed(() => {
  const buckets = new Map()
  for (const item of items.value) {
    const date = new Date(item.time)
    if (Number.isNaN(date.getTime())) continue
    const minutes = Math.min(DAY_END, Math.max(DAY_START, date.getHours() * 60 + date.getMinutes()))
    const key = Math.floor(minutes / 60)
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push({ ...item, minutes })
  }
  const groups = [...buckets.values()].map((list) => list.sort((a, b) => a.minutes - b.minutes)).sort((a, b) => a[0].minutes - b[0].minutes)
  const merged = []
  for (const group of groups) {
    const center = group.reduce((sum, it) => sum + it.minutes, 0) / group.length
    const last = merged[merged.length - 1]
    if (last && center - last.minutes < 75) {
      last.minutes = (last.minutes * last.list.length + center * group.length) / (last.list.length + group.length)
      last.list.push(...group)
      continue
    }
    merged.push({ minutes: center, list: [...group] })
  }
  return merged.slice(0, 8).map((node) => {
    const latest = node.list[node.list.length - 1]
    return {
      id: latest.id,
      left: Math.min(94, Math.max(6, ((node.minutes - DAY_START) / (DAY_END - DAY_START)) * 100)),
      time: latest.time,
      label: latest.label,
      type: latest.type,
      count: node.list.length,
      danger: node.list.some((it) => ['warning', 'critical'].includes(it.severity) || it.type === 'alert'),
    }
  })
})
const timeTicks = ['05:00','08:00','11:00','14:00','17:00','20:00','23:00']

function shiftDay(offset) { const date = new Date(`${currentDate.value}T00:00:00`); date.setDate(date.getDate()+offset); currentDate.value = date.toISOString().slice(0,10) }
function timeOf(value) { const d = new Date(value); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}` }
function dayOf(value) { const d = new Date(value); return `${d.getMonth()+1}月${d.getDate()}日` }
function iconOf(type, label = '') { if (label.includes('起床')) return 'bed'; return { canteen_present:'restaurant', canteen_absent:'no_meals', view:'favorite', event:'directions_walk', device:'sensor_door', alert:'error' }[type] || 'schedule' }
function sourceOf(type) { return type?.startsWith('canteen') ? '食堂' : type === 'view' ? '小程序' : type === 'alert' ? '关怀事件' : type === 'device' ? '智能设备' : '社区' }

async function load() {
  if (isToday.value) { items.value = props.initialItems; return }
  loading.value = true
  try {
    const data = await getElderDayActivity(props.elderId, currentDate.value)
    items.value = (data.signals || []).map((item,index) => ({ ...item, id:`${currentDate.value}-${index}`, time:new Date(`${currentDate.value}T${String(item.hour).padStart(2,'0')}:${String(item.minute || 0).padStart(2,'0')}:00`).toISOString() }))
  } catch { items.value = [] } finally { loading.value = false }
}

watch([currentDate, () => props.initialItems], load, { immediate:true })
</script>

<style scoped>
.activity-card { display: flex; min-height: 0; flex-direction: column; overflow-x: hidden; overflow-y: auto; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.8); }.activity-card header { display: flex; min-height: 62px; flex: none; align-items: center; justify-content: space-between; padding: 12px 18px 8px; }.activity-card h2, .recent-title { margin: 0; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }.date-picker { display: grid; width: 172px; height: 32px; grid-template-columns: 34px 1fr 34px; align-items: stretch; overflow: hidden; border: 1px solid #e2dcd5; border-radius: 7px; background: #fff; }.date-picker button { display: grid; width: 34px; height: 100%; padding: 0; place-items: center; border: 0; color: #43516a; background: transparent; cursor: pointer; }.date-picker button .material-symbols-outlined { display: block; font-size: 20px; line-height: 1; }.date-picker button:disabled { opacity: .35; }.date-picker > span { display: grid; min-width: 0; place-items: center; color: #536076; font-size: 12px; line-height: 1; text-align: center; }
.activity-track { position: relative; min-height: 140px; flex: none; padding: 7px 18px 16px; }.time-ruler { position: relative; display: grid; grid-template-columns: repeat(7,1fr); height: 45px; color: #526078; }.time-ruler::after { content: ''; position: absolute; right: 0; bottom: 9px; left: 0; height: 2px; background: #ded8d1; }.time-ruler span { position: relative; display: grid; justify-items: center; font-size: 10px; font-weight: 400; }.time-ruler span:first-child { justify-items: start; }.time-ruler span:last-child { justify-items: end; }.time-ruler b { font-weight: 500; }.time-ruler i { position: absolute; z-index: 1; bottom: 5px; left: 50%; width: 1px; height: 9px; background: #d0c9c2; transform: translateX(-50%); }.time-ruler span:first-child i { left: 8px; }.time-ruler span:last-child i { right: 8px; left: auto; }.activity-events { position: relative; height: 96px; margin-top: -12px; }.event-pin { position: absolute; top: 0; display: grid; width: 104px; grid-template-rows: 8px 38px 16px 18px; justify-items: center; color: #3f4d63; transform: translateX(-50%); --event-color: #5e8a75; }.event-pin::before { content: ''; position: absolute; top: 4px; left: 50%; z-index: 0; width: 1px; height: 22px; background: var(--event-color); transform: translateX(-50%); }.event-pin .event-node { position: relative; z-index: 2; width: 7px; height: 7px; border-radius: 50%; background: var(--event-color); }.event-pin .activity-icon { position: relative; z-index: 1; display: grid; box-sizing: border-box; width: 35px; height: 35px; place-items: center; border: 2px solid var(--event-color); border-radius: 50%; color: var(--event-color); background: #fff; font-size: 21px; }.event-pin time { color: #334158; font-size: 11px; font-weight: 800; }.event-pin b { max-width: 104px; overflow: hidden; font-size: 12px; font-weight: 600; text-align: center; text-overflow: ellipsis; white-space: nowrap; }.event-count { position: absolute; top: -5px; right: -3px; display: grid; min-width: 15px; height: 15px; padding: 0 3px; place-items: center; border-radius: 999px; color: #fff; background: var(--event-color); font-size: 9px; font-style: normal; font-weight: 800; }.event--danger { --event-color: #dc4f34; }.event--danger time, .event--danger b { color: #dc4f34; }.activity-track-empty { display: grid; min-height: 80px; place-items: center; color: #8a919b; font-size: 13px; }
.recent-title { flex: none; margin: 0 18px; padding-top: 12px; border-top: 1px solid #eee8e2; }.recent-table { margin: 10px 18px 0; }.recent-head, .recent-row { display: grid; grid-template-columns: 180px 1fr 100px; align-items: center; }.recent-head { padding: 9px 12px; border-radius: 7px; color: #657083; background: linear-gradient(90deg,#faf1e9,#fbf7f2); font-size: 12px; }.recent-head span:first-child { padding-left: 28px; }.recent-row { position: relative; min-height: 38px; padding: 0 12px; color: #536077; font-size: 12px; }.recent-row::after { content: ''; position: absolute; right: 0; bottom: 0; left: 40px; height: 1px; background: #eee9e4; }.recent-row time { position: relative; display: grid; align-self: stretch; grid-template-columns: 74px auto; align-items: center; padding-left: 28px; font-style: normal; }.recent-row time::before { content: ''; position: absolute; top: 0; bottom: 0; left: 8px; width: 1px; background: rgba(216,90,66,.3); transform: translateX(-50%); }.recent-row.first time::before { top: 50%; }.recent-row.last time::before { bottom: 50%; }.recent-row .timeline-dot { position: absolute; z-index: 1; top: 50%; left: 4px; box-sizing: border-box; width: 8px; height: 8px; border: 2px solid #d85a42; border-radius: 50%; background: #fff; transform: translateY(-50%); }.recent-row > span { display: flex; align-items: center; gap: 9px; color: #445167; }.recent-row > span i { color: #56826a; font-size: 20px; }.recent-row em { font-style: normal; }.recent-empty, .activity-state { display: grid; min-height: 100px; place-items: center; color: #91867c; font-size: 13px; }.all-activity { display: flex; min-height: 42px; flex: none; align-items: center; justify-content: space-between; margin: 14px 18px 14px; padding: 0 14px; border: 0; border-radius: 7px; color: #566176; background: linear-gradient(90deg,#faf1e9,#fbf7f2); font-size: 12px; cursor: pointer; }
</style>
