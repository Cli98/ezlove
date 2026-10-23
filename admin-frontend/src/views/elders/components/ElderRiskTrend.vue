<template>
  <section class="risk-trend-card">
    <header class="trend-head">
      <h2>安全曲线</h2>
      <span v-if="delta" :class="['trend-delta', delta.tone]">{{ delta.text }}</span>
    </header>

    <div v-if="loading" class="trend-state">
      <span class="material-symbols-outlined spinning">progress_activity</span>
      <p>正在读取每日快照…</p>
    </div>

    <div v-else-if="failed" class="trend-state">
      <span class="material-symbols-outlined">error</span>
      <p>快照读取失败，稍后重试</p>
    </div>

    <div v-else-if="items.length < 2" class="trend-state">
      <span class="material-symbols-outlined">event_note</span>
      <p>暂无足够的每日快照<br />明日起将显示 30 天趋势</p>
    </div>

    <template v-else>
      <svg
        class="trend-svg"
        viewBox="0 0 320 108"
        preserveAspectRatio="none"
        role="img"
        :aria-label="`近 ${items.length} 日风险分数趋势`"
      >
        <defs>
          <linearGradient id="risk-trend-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="tone.color" stop-opacity="0.24" />
            <stop offset="100%" :stop-color="tone.color" stop-opacity="0" />
          </linearGradient>
        </defs>
        <rect x="0" y="8" width="320" height="16" fill="#b03a2e" fill-opacity="0.07" />
        <rect x="0" y="24" width="320" height="16" fill="#c75a3d" fill-opacity="0.06" />
        <rect x="0" y="40" width="320" height="24" fill="#d68f30" fill-opacity="0.07" />
        <rect x="0" y="64" width="320" height="24" fill="#56826a" fill-opacity="0.08" />
        <path :d="areaPath" fill="url(#risk-trend-fill)" />
        <polyline
          :points="points"
          fill="none"
          :stroke="tone.color"
          stroke-width="2.2"
          stroke-linecap="round"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
        />
        <circle :cx="lastPoint.x" :cy="lastPoint.y" r="3.2" :fill="tone.color" stroke="#fff" stroke-width="1.6" />
      </svg>

      <footer class="trend-foot">
        <span class="trend-current" :style="{ color: tone.color, background: tone.bg }">
          当前 {{ current.score }} 分 · {{ levelLabel(current.level) }}
        </span>
        <small>{{ rangeText }}</small>
      </footer>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getElderRiskHistory } from '@/api/devices'

const props = defineProps({ elderId: { type: String, required: true } })

const LEVEL_TONES = {
  normal: { color: '#56826a', bg: '#e6f0e9' },
  attention: { color: '#d1842b', bg: '#fbedd9' },
  warning: { color: '#c75a3d', bg: '#fae7df' },
  critical: { color: '#a5321f', bg: '#f8ddd5' },
}

const loading = ref(false)
const failed = ref(false)
const items = ref([])

const current = computed(() => items.value[items.value.length - 1] || null)
const tone = computed(() => LEVEL_TONES[current.value?.level] || LEVEL_TONES.normal)

// score 0-100 映射到 y 8-88（分数越高风险越高，曲线越靠上）
const coords = computed(() => {
  const list = items.value
  if (list.length < 2) return []
  const stepX = 312 / (list.length - 1)
  return list.map((item, index) => ({
    x: 4 + index * stepX,
    y: 88 - (Math.min(100, Math.max(0, item.score)) / 100) * 80,
  }))
})

const points = computed(() => coords.value.map(point => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' '))

const areaPath = computed(() => {
  if (!coords.value.length) return ''
  const line = coords.value.map(point => `L ${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ')
  return `M 4,88 ${line} L 316,88 Z`
})

const lastPoint = computed(() => coords.value[coords.value.length - 1] || { x: 316, y: 88 })

const delta = computed(() => {
  const list = items.value
  if (list.length < 2) return null
  const diff = list[list.length - 1].score - list[0].score
  if (Math.abs(diff) < 3) return { text: '近期持平', tone: 'flat' }
  return diff > 0
    ? { text: `较首日上升 ${Math.round(diff)} 分`, tone: 'up' }
    : { text: `较首日下降 ${Math.round(-diff)} 分`, tone: 'down' }
})

const rangeText = computed(() => {
  const list = items.value
  if (!list.length) return ''
  return `${formatDay(list[0].date)} - ${formatDay(list[list.length - 1].date)}`
})

function levelLabel(level) {
  return { normal: '平稳', attention: '需关注', warning: '较高', critical: '高风险' }[level] || '待评估'
}

function formatDay(value) {
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

async function load() {
  loading.value = true
  failed.value = false
  try {
    const res = await getElderRiskHistory(props.elderId, 30)
    items.value = res?.items || []
  } catch {
    failed.value = true
    items.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.elderId, load)
onMounted(load)
</script>

<style scoped>
.risk-trend-card { padding: 14px 18px 13px; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.8); }
.trend-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.trend-head h2 { margin: 0; color: #172942; font: 700 17px 'Songti SC','STSong',serif; }
.trend-delta { display: inline-flex; height: 24px; align-items: center; padding: 0 9px; border-radius: 6px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.trend-delta.up { color: #c75a3d; background: #fae7df; }
.trend-delta.down { color: #56826a; background: #e6f0e9; }
.trend-delta.flat { color: #8d8a86; background: #f2eee9; }
.trend-svg { display: block; width: 100%; height: 92px; margin-top: 10px; border-radius: 7px; }
.trend-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 9px; }
.trend-current { display: inline-flex; height: 25px; align-items: center; padding: 0 10px; border-radius: 7px; font-size: 11.5px; font-weight: 800; }
.trend-foot small { color: #9a9188; font-size: 11px; }
.trend-state { display: grid; min-height: 118px; place-items: center; align-content: center; gap: 6px; color: #91867c; font-size: 12px; text-align: center; }
.trend-state > span { font-size: 28px; }
.trend-state p { margin: 0; line-height: 1.55; }
.spinning { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
</style>