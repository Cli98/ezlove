<template>
  <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="font-headline text-lg font-bold text-on-surface">日活动轨迹</h3>
      <div class="flex items-center gap-2">
        <button class="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center hover:bg-outline-variant/20" @click="prevDay">
          <span class="material-symbols-outlined text-sm">chevron_left</span>
        </button>
        <span class="text-sm font-semibold text-on-surface min-w-[90px] text-center">{{ displayDate }}</span>
        <button
          class="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center hover:bg-outline-variant/20"
          :disabled="isToday"
          :class="{ 'opacity-30': isToday }"
          @click="nextDay"
        >
          <span class="material-symbols-outlined text-sm">chevron_right</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-8 text-inactive-gray text-sm gap-2">
      <div class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      加载中...
    </div>

    <div v-else>
      <!-- SVG Timeline -->
      <div class="overflow-x-auto">
        <svg :viewBox="`0 0 ${svgWidth} 80`" class="w-full" style="min-width: 600px">
          <!-- Background -->
          <rect x="40" y="30" :width="svgWidth - 80" height="20" rx="4" fill="#F5F0EB" />

          <!-- Gap highlights -->
          <rect
            v-for="(gap, i) in data.gaps"
            :key="'gap-' + i"
            :x="hourToX(gap.start_hour)"
            y="28"
            :width="hourToX(gap.end_hour) - hourToX(gap.start_hour)"
            height="24"
            rx="4"
            :fill="gap.severity === 'red' ? '#C44D3E20' : '#D4A24E20'"
            :stroke="gap.severity === 'red' ? '#C44D3E' : '#D4A24E'"
            stroke-width="1"
            stroke-dasharray="4 2"
          />

          <!-- Hour marks -->
          <g v-for="h in hourMarks" :key="h">
            <line :x1="hourToX(h)" y1="28" :x2="hourToX(h)" y2="52" stroke="#E5DED5" stroke-width="1" />
            <text :x="hourToX(h)" y="68" text-anchor="middle" fill="#999" font-size="10">{{ h }}:00</text>
          </g>

          <!-- Signal dots -->
          <g v-for="(sig, i) in data.signals" :key="'sig-' + i">
            <circle
              :cx="hourToX(sig.hour + (sig.minute || 0) / 60)"
              cy="40"
              r="6"
              :fill="signalColor(sig)"
              stroke="white"
              stroke-width="2"
            />
            <text
              :x="hourToX(sig.hour + (sig.minute || 0) / 60)"
              y="22"
              text-anchor="middle"
              :fill="signalColor(sig)"
              font-size="9"
              font-weight="600"
            >{{ sig.label }}</text>
          </g>
        </svg>
      </div>

      <!-- Legend -->
      <div class="flex flex-wrap gap-4 mt-3 text-[10px] font-medium text-inactive-gray">
        <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-secondary"></span> 食堂</div>
        <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-accent"></span> 查看牵挂</div>
        <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-primary"></span> 事件/告警</div>
        <div class="flex items-center gap-1"><span class="w-6 h-2.5 rounded border border-dashed border-accent bg-accent/10"></span> 6h+空白</div>
        <div class="flex items-center gap-1"><span class="w-6 h-2.5 rounded border border-dashed border-primary bg-primary/10"></span> 12h+空白</div>
      </div>

      <!-- No signals -->
      <div v-if="!data.signals?.length" class="text-center py-4 text-inactive-gray text-sm">
        该日无活动记录
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { getElderDayActivity } from '@/api/community'

const props = defineProps({
  elderId: { type: String, required: true },
})

const currentDate = ref(new Date().toISOString().slice(0, 10))
const data = ref({ signals: [], gaps: [] })
const loading = ref(false)

const svgWidth = 700

const displayDate = computed(() => {
  const d = new Date(currentDate.value + 'T00:00:00')
  return `${d.getMonth() + 1}月${d.getDate()}日`
})

const isToday = computed(() => currentDate.value === new Date().toISOString().slice(0, 10))

const hourMarks = [6, 8, 10, 12, 14, 16, 18, 20, 22]

function hourToX(h) {
  const startH = 5
  const endH = 23
  return 40 + ((h - startH) / (endH - startH)) * (svgWidth - 80)
}

function signalColor(sig) {
  if (sig.type === 'canteen') return '#6B8F71'
  if (sig.type === 'view') return '#D4A24E'
  return '#C44D3E'
}

function prevDay() {
  const d = new Date(currentDate.value + 'T00:00:00')
  d.setDate(d.getDate() - 1)
  currentDate.value = d.toISOString().slice(0, 10)
}

function nextDay() {
  if (isToday.value) return
  const d = new Date(currentDate.value + 'T00:00:00')
  d.setDate(d.getDate() + 1)
  currentDate.value = d.toISOString().slice(0, 10)
}

async function loadData() {
  loading.value = true
  try {
    data.value = await getElderDayActivity(props.elderId, currentDate.value)
  } catch (e) {
    data.value = { signals: [], gaps: [] }
  } finally {
    loading.value = false
  }
}

watch(currentDate, loadData, { immediate: true })
</script>
