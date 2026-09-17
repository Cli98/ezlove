<template>
  <div>
    <!-- Loading State -->
    <div v-if="store.loading && !store.data" class="flex items-center justify-center py-32">
      <div class="inline-flex items-center gap-3 text-on-surface-variant">
        <svg class="animate-spin w-6 h-6" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
        <span class="text-sm font-medium">加载看板数据...</span>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="store.error && !store.data" class="flex items-center justify-center py-32">
      <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-8 text-center max-w-sm">
        <span class="material-symbols-outlined text-4xl text-primary mb-3 block">error</span>
        <p class="text-sm font-semibold text-on-surface mb-1">数据加载失败</p>
        <p class="text-xs text-on-surface-variant mb-5">{{ store.error.message || store.error || '网络异常，请稍后再试' }}</p>
        <button
          class="px-6 py-2.5 rounded-xl text-sm font-semibold bg-primary text-white shadow-sm hover:bg-terracotta transition-colors"
          @click="store.load()"
        >重新加载</button>
      </div>
    </div>

    <!-- Presentation Mode: Floating Exit Button -->
    <button
      v-if="store.presentationMode"
      class="fixed top-4 right-4 z-50 bg-on-surface/80 text-white px-4 py-2 rounded-full text-sm font-bold flex items-center gap-2 hover:bg-on-surface transition-colors shadow-lg backdrop-blur-md"
      @click="exitPresentation"
    >
      <span class="material-symbols-outlined text-sm">fullscreen_exit</span>
      退出全屏
    </button>

    <!-- Presentation Mode: Community Banner -->
    <div v-if="store.presentationMode" class="bg-gradient-to-r from-charcoal to-charcoal/90 text-white rounded-2xl p-6 mb-6 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <div>
          <h1 class="font-headline text-3xl font-bold">易挂念</h1>
          <p class="text-white/60 text-sm mt-1">{{ store.data?.community_name || '社区康养管理系统' }}</p>
        </div>
        <div class="h-12 w-px bg-white/20"></div>
        <div class="flex gap-8">
          <div class="text-center">
            <div class="serif-num text-3xl font-bold">{{ store.data?.total_elders || 0 }}</div>
            <div class="text-xs text-white/70 mt-1">总人数</div>
          </div>
          <div class="text-center">
            <div class="serif-num text-3xl font-bold text-secondary">{{ store.data?.today_active_count || 0 }}</div>
            <div class="text-xs text-white/70 mt-1">今日活跃</div>
          </div>
          <div class="text-center">
            <div class="serif-num text-3xl font-bold" :class="(store.data?.today_active_rate || 0) >= 70 ? 'text-secondary' : 'text-accent'">{{ store.data?.today_active_rate || 0 }}%</div>
            <div class="text-xs text-white/70 mt-1">活跃率</div>
          </div>
          <div class="text-center">
            <div class="serif-num text-3xl font-bold" :class="(store.data?.pending_events || 0) > 0 ? 'text-primary' : 'text-secondary'">{{ store.data?.pending_events || 0 }}</div>
            <div class="text-xs text-white/70 mt-1">待处理告警</div>
          </div>
        </div>
      </div>
      <div class="text-right">
        <div class="serif-num text-2xl font-bold tabular-nums">{{ currentTime }}</div>
        <div class="text-xs text-white/60 mt-1">{{ currentDate }}</div>
      </div>
    </div>

    <!-- Live Status Bar -->
    <div v-if="!store.presentationMode && store.data" class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <h2 class="font-headline text-2xl font-bold text-on-surface">社区看板</h2>
        <div class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary/10">
          <span :class="['w-2 h-2 rounded-full bg-secondary transition-all duration-500', dataFresh ? 'scale-150 shadow-[0_0_6px_rgba(107,143,113,0.6)]' : '']"></span>
          <span class="text-xs font-medium text-secondary">实时</span>
        </div>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-on-surface-variant hover:bg-surface-container transition-colors"
        @click="enterPresentation"
      >
        <span class="material-symbols-outlined text-lg">fullscreen</span>
        全屏展示
        <span class="text-[10px] text-inactive-gray ml-1 font-normal">(F11)</span>
      </button>
    </div>

    <!-- 1. Top Stat Row: 6 cards (hidden in presentation mode) -->
    <div v-if="!store.presentationMode" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
      <div class="bg-surface p-5 rounded-2xl shadow-sm border border-outline-variant/20 hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-bold text-inactive-gray tracking-wider uppercase">总人数</span>
          <span class="material-symbols-outlined text-inactive-gray">groups</span>
        </div>
        <div class="serif-num text-3xl font-bold text-on-surface">{{ animatedValues.total ?? 0 }}</div>
      </div>
      <div class="bg-surface p-5 rounded-2xl shadow-sm border border-outline-variant/20 hover:shadow-md transition-shadow border-l-4 border-l-primary">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-bold text-primary tracking-wider uppercase">A级</span>
          <span class="material-symbols-outlined text-primary">emergency_home</span>
        </div>
        <div class="serif-num text-3xl font-bold text-on-surface">{{ animatedValues.a ?? 0 }}</div>
      </div>
      <div class="bg-surface p-5 rounded-2xl shadow-sm border border-outline-variant/20 hover:shadow-md transition-shadow border-l-4 border-l-accent">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-bold text-accent tracking-wider uppercase">B级</span>
          <span class="material-symbols-outlined text-accent">medical_services</span>
        </div>
        <div class="serif-num text-3xl font-bold text-on-surface">{{ animatedValues.b ?? 0 }}</div>
      </div>
      <div class="bg-surface p-5 rounded-2xl shadow-sm border border-outline-variant/20 hover:shadow-md transition-shadow border-l-4 border-l-secondary">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-bold text-secondary tracking-wider uppercase">C级</span>
          <span class="material-symbols-outlined text-secondary">health_and_safety</span>
        </div>
        <div class="serif-num text-3xl font-bold text-on-surface">{{ animatedValues.c ?? 0 }}</div>
      </div>
      <div class="bg-surface p-5 rounded-2xl shadow-sm border border-outline-variant/20 hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-bold text-on-surface-variant tracking-wider uppercase">今日活跃</span>
          <span class="material-symbols-outlined text-on-surface-variant">bolt</span>
        </div>
        <div class="serif-num text-3xl font-bold text-on-surface">{{ animatedValues.active ?? 0 }}</div>
        <SparkLine v-if="dailyActiveCounts.length > 1" :data="dailyActiveCounts" :width="100" :height="32" color="#6B8F71" class="mt-1" />
      </div>
      <div class="bg-surface p-5 rounded-2xl shadow-sm border border-outline-variant/20 hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-bold text-on-surface-variant tracking-wider uppercase">活跃率</span>
          <span class="material-symbols-outlined text-on-surface-variant">analytics</span>
        </div>
        <div class="serif-num text-3xl font-bold text-on-surface">{{ animatedValues.rate ?? 0 }}%</div>
        <SparkLine v-if="dailyActiveRates.length > 1" :data="dailyActiveRates" :width="100" :height="32" color="#6B8F71" class="mt-1" />
      </div>
    </div>

    <!-- Main Layout -->
    <div :class="store.presentationMode ? 'flex flex-col gap-6' : 'flex flex-col lg:flex-row gap-8'">
      <!-- Left: WorkStation + Buildings -->
      <div class="flex-1 space-y-8">
        <!-- WorkStation (hidden in presentation) -->
        <WorkStation
          v-if="!store.presentationMode"
          :workstation="store.data?.workstation"
          :active-area="store.activeArea"
          @confirm="handleConfirm"
        />

        <!-- Building Overview -->
        <div class="bg-surface p-8 rounded-3xl shadow-sm border border-outline-variant/20">
          <div class="flex justify-between items-center mb-6">
            <div>
              <h3 class="font-headline text-2xl font-bold text-on-surface">楼栋总览</h3>
              <p class="text-on-surface-variant text-sm mt-1">{{ store.presentationMode ? '颜色深浅表示活跃率' : '点击楼栋查看老人详情' }}</p>
            </div>
            <div class="flex items-center gap-4">
              <button
                v-if="!store.presentationMode"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-on-surface-variant hover:bg-surface-container transition-colors"
                @click="enterPresentation"
              >
                <span class="material-symbols-outlined text-base">fullscreen</span>
                全屏展示
              </button>
              <div class="flex items-center gap-3 text-[10px] font-medium text-inactive-gray">
                <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-secondary"></span> 正常</div>
                <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-accent"></span> 关注</div>
                <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-primary"></span> 异常</div>
              </div>
            </div>
          </div>

          <!-- Area tabs -->
          <div class="flex gap-2 mb-6">
            <button
              v-for="area in areas"
              :key="area.name"
              :class="[
                'px-4 py-2 rounded-xl text-sm font-bold transition-all',
                store.activeArea === area.name
                  ? 'bg-on-surface text-white shadow-md'
                  : 'bg-surface-container text-on-surface-variant hover:bg-outline-variant/20',
              ]"
              @click="store.activeArea = area.name"
            >
              {{ area.name }}
              <span class="text-xs font-normal opacity-70 ml-1">{{ areaElderCount(area) }}人</span>
            </button>
          </div>

          <!-- Building cards / heatmap -->
          <div v-if="currentArea" :class="[
            'grid gap-4',
            store.presentationMode
              ? 'grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8'
              : 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5'
          ]">
            <template v-if="store.presentationMode">
              <div
                v-for="(b, idx) in currentArea.buildings"
                :key="b.name"
                class="relative p-3 rounded-xl text-center cursor-pointer transition-all hover:scale-105 hover:shadow-md heat-tile-enter"
                :style="{ backgroundColor: heatColor(b.active_rate), animationDelay: `${idx * 40}ms` }"
                @click="store.loadBuildingElders(b.name)"
              >
                <div class="text-sm font-bold text-white drop-shadow">{{ shortBuildingName(b.name) }}</div>
                <div class="serif-num text-lg font-bold text-white drop-shadow">{{ b.active_rate }}%</div>
                <div class="text-[10px] text-white/80">{{ b.elder_count }}人</div>
                <div v-if="b.alert_count > 0" class="absolute top-1 right-1 w-4 h-4 bg-white rounded-full flex items-center justify-center">
                  <span class="text-[9px] font-bold text-primary">{{ b.alert_count }}</span>
                </div>
              </div>
            </template>
            <template v-else>
              <BuildingCard
                v-for="b in currentArea.buildings"
                :key="b.name"
                :building="b"
                :trends="buildingTrends[b.name]"
                :expanded="store.expandedBuilding === b.name"
                @toggle="store.loadBuildingElders(b.name)"
              />
            </template>
          </div>

          <!-- Expanded building tile grid -->
          <ElderTileGrid
            v-if="store.expandedBuilding"
            :building="store.expandedBuilding"
            :elders="store.buildingElders"
            :loading="store.buildingLoading"
            class="mt-6"
            @close="store.expandedBuilding = null"
          />
        </div>
      </div>

      <!-- Right Sidebar / Bottom Row in presentation -->
      <div :class="store.presentationMode ? 'grid grid-cols-2 lg:grid-cols-4 gap-6' : 'w-full lg:w-80 space-y-6'">
        <!-- Care Distribution Donut -->
        <div class="bg-surface p-6 rounded-3xl shadow-sm border border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface mb-6">分级分布</h3>
          <div class="relative w-48 h-48 mx-auto mb-6 flex items-center justify-center">
            <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" fill="transparent" r="15.9" stroke="#E5DED5" stroke-width="3"></circle>
              <circle v-if="totalElders > 0" cx="18" cy="18" fill="transparent" r="15.9" stroke="#C44D3E"
                :stroke-dasharray="`${(levelA / totalElders) * 100} 100`" stroke-width="3"
                style="transition: stroke-dasharray 1s ease-out"></circle>
              <circle v-if="totalElders > 0" cx="18" cy="18" fill="transparent" r="15.9" stroke="#D4A24E"
                :stroke-dasharray="`${(levelB / totalElders) * 100} 100`"
                :stroke-dashoffset="`-${(levelA / totalElders) * 100}`" stroke-width="3"
                style="transition: stroke-dasharray 1s ease-out 0.2s, stroke-dashoffset 1s ease-out 0.2s"></circle>
              <circle v-if="totalElders > 0" cx="18" cy="18" fill="transparent" r="15.9" stroke="#6B8F71"
                :stroke-dasharray="`${(levelC / totalElders) * 100} 100`"
                :stroke-dashoffset="`-${((levelA + levelB) / totalElders) * 100}`" stroke-width="3"
                style="transition: stroke-dasharray 1s ease-out 0.4s, stroke-dashoffset 1s ease-out 0.4s"></circle>
            </svg>
            <div class="absolute text-center">
              <span class="serif-num text-2xl font-bold block">{{ totalElders }}</span>
              <span class="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">总计</span>
            </div>
          </div>
          <div class="space-y-3">
            <div class="flex justify-between items-center text-sm">
              <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-primary"></span> A级</div>
              <span class="serif-num font-bold">{{ totalElders > 0 ? ((levelA / totalElders) * 100).toFixed(1) : '0.0' }}%</span>
            </div>
            <div class="flex justify-between items-center text-sm">
              <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-accent"></span> B级</div>
              <span class="serif-num font-bold">{{ totalElders > 0 ? ((levelB / totalElders) * 100).toFixed(1) : '0.0' }}%</span>
            </div>
            <div class="flex justify-between items-center text-sm">
              <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-secondary"></span> C级</div>
              <span class="serif-num font-bold">{{ totalElders > 0 ? ((levelC / totalElders) * 100).toFixed(1) : '0.0' }}%</span>
            </div>
          </div>
        </div>

        <!-- Risk Overview -->
        <div v-if="riskDistribution" class="bg-surface p-6 rounded-3xl shadow-sm border border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface mb-4">风险概况</h3>
          <div class="space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-primary"></span>
                <span class="text-sm text-on-surface">高危</span>
              </div>
              <span class="serif-num text-sm font-bold text-on-surface">{{ riskDistribution.critical || 0 }}</span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-warning"></span>
                <span class="text-sm text-on-surface">预警</span>
              </div>
              <span class="serif-num text-sm font-bold text-on-surface">{{ riskDistribution.warning || 0 }}</span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-accent"></span>
                <span class="text-sm text-on-surface">关注</span>
              </div>
              <span class="serif-num text-sm font-bold text-on-surface">{{ riskDistribution.attention || 0 }}</span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-secondary"></span>
                <span class="text-sm text-on-surface">正常</span>
              </div>
              <span class="serif-num text-sm font-bold text-on-surface">{{ riskDistribution.normal || 0 }}</span>
            </div>
          </div>
        </div>

        <!-- 7-Day Trend Chart -->
        <div v-if="dailyActiveRates.length > 1" class="bg-surface p-6 rounded-3xl shadow-sm border border-outline-variant/20">
          <h3 :class="store.presentationMode ? 'font-headline text-xl font-bold text-on-surface mb-4' : 'font-headline text-lg font-bold text-on-surface mb-4'">7 天趋势</h3>
          <svg viewBox="0 0 240 120" :class="store.presentationMode ? 'w-full min-h-[240px]' : 'w-full'">
            <defs>
              <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#6B8F71" stop-opacity="0.2" />
                <stop offset="100%" stop-color="#6B8F71" stop-opacity="0" />
              </linearGradient>
            </defs>
            <!-- Grid lines -->
            <line v-for="i in 3" :key="'g'+i" x1="30" :y1="10 + (i-1)*40" x2="235" :y2="10 + (i-1)*40" stroke="#E5DED5" stroke-width="0.5" stroke-dasharray="3,3" />
            <!-- Y labels -->
            <text v-for="(val, i) in trendYLabels" :key="'yl'+i" x="26" :y="14 + i*40" text-anchor="end" fill="#9A8E82" font-size="8">{{ val }}%</text>
            <!-- Fill polygon -->
            <polygon :points="trendFillPoints" fill="url(#trendFill)" />
            <!-- Line -->
            <polyline :points="trendLinePoints" fill="none" stroke="#6B8F71" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            <!-- Dots -->
            <circle
              v-for="(pt, i) in trendPoints"
              :key="'d'+i"
              :cx="pt[0]" :cy="pt[1]"
              r="3" fill="#6B8F71" stroke="white" stroke-width="1.5"
            />
            <!-- X labels -->
            <text
              v-for="(label, i) in trendXLabels"
              :key="'xl'+i"
              :x="30 + i * (205 / (trendXLabels.length > 1 ? trendXLabels.length - 1 : 1))"
              y="115"
              text-anchor="middle"
              fill="#9A8E82"
              font-size="8"
            >{{ label }}</text>
          </svg>
          <!-- Alert mini bars -->
          <div v-if="dailyAlertNew.length" class="mt-3 pt-3 border-t border-outline-variant/10">
            <div class="flex items-center justify-between text-[10px] text-inactive-gray mb-1.5">
              <span>告警趋势</span>
              <span>最高 {{ maxAlert }}</span>
            </div>
            <div class="flex items-end gap-1 h-6">
              <div
                v-for="(v, i) in dailyAlertNew"
                :key="'ab'+i"
                class="flex-1 bg-primary/40 rounded-sm transition-all"
                :style="{ height: maxAlert > 0 ? (v / maxAlert * 100) + '%' : '0%' }"
              ></div>
            </div>
          </div>
        </div>

        <!-- Today Quick View (hidden in presentation — banner has the data) -->
        <div v-if="!store.presentationMode" class="bg-surface p-6 rounded-3xl shadow-sm border border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface mb-4">今日速览</h3>
          <div class="space-y-3">
            <router-link to="/elders" class="flex gap-3 p-3 rounded-xl bg-primary/5 hover:bg-primary/10 transition-colors cursor-pointer">
              <div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-white text-sm">ring_volume</span>
              </div>
              <div>
                <p class="text-sm font-bold text-on-surface">{{ pendingConfirmCount }} 人待确认</p>
                <p class="text-[10px] text-inactive-gray">A/B级今日未活跃</p>
              </div>
            </router-link>
            <router-link to="/events" class="flex gap-3 p-3 rounded-xl bg-accent/5 hover:bg-accent/10 transition-colors cursor-pointer">
              <div class="w-8 h-8 rounded-lg bg-accent flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-white text-sm">warning</span>
              </div>
              <div>
                <p class="text-sm font-bold text-on-surface">{{ store.data?.pending_events || 0 }} 条告警</p>
                <p class="text-[10px] text-inactive-gray">待处理事件</p>
              </div>
            </router-link>
            <router-link to="/canteen" class="flex gap-3 p-3 rounded-xl bg-secondary/5 hover:bg-secondary/10 transition-colors cursor-pointer">
              <div class="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-white text-sm">restaurant</span>
              </div>
              <div>
                <p class="text-sm font-bold text-on-surface">食堂管理</p>
                <p class="text-[10px] text-inactive-gray">今日出勤 · 缺席预警</p>
              </div>
            </router-link>
          </div>
        </div>

        <!-- System Status (hidden in presentation) -->
        <div v-if="!store.presentationMode" class="p-6 bg-surface-container rounded-3xl border border-outline-variant/30 text-center">
          <span class="inline-block w-2 h-2 rounded-full bg-secondary mb-2 animate-pulse"></span>
          <p class="text-xs font-bold text-on-surface tracking-wider uppercase">系统正常</p>
          <p class="text-[10px] text-on-surface-variant mt-1">上次同步: {{ currentTime }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useDashboardStore } from '@/stores/dashboard'
import WorkStation from './components/WorkStation.vue'
import BuildingCard from './components/BuildingCard.vue'
import ElderTileGrid from './components/ElderTileGrid.vue'
import SparkLine from './components/SparkLine.vue'

const store = useDashboardStore()
const dataFresh = ref(false)

onMounted(() => store.load())

let refreshInterval
onMounted(() => {
  refreshInterval = setInterval(async () => {
    try {
      await store.load()
      dataFresh.value = true
      setTimeout(() => { dataFresh.value = false }, 2000)
    } catch {
      // network hiccup — silently skip this refresh cycle
    }
  }, 30000)
})
onUnmounted(() => clearInterval(refreshInterval))

const currentTime = ref(new Date().toLocaleTimeString('zh-CN', { hour12: true }))
const currentDate = ref(new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }))
let timeInterval
onMounted(() => {
  timeInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour12: true })
  }, 1000)
})
onUnmounted(() => clearInterval(timeInterval))

function enterPresentation() {
  store.presentationMode = true
  document.documentElement.requestFullscreen?.()
}

function exitPresentation() {
  store.presentationMode = false
  if (document.fullscreenElement) document.exitFullscreen?.()
}

function handleKeyboard(e) {
  if (e.key === 'Escape') exitPresentation()
  if (e.key === 'F11') {
    e.preventDefault()
    if (store.presentationMode) exitPresentation()
    else enterPresentation()
  }
}

function handleFullscreenChange() {
  if (!document.fullscreenElement && store.presentationMode) {
    store.presentationMode = false
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyboard)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboard)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})

function heatColor(rate) {
  if (rate >= 80) return '#2D8A4E'
  if (rate >= 60) return '#6B8F71'
  if (rate >= 40) return '#D4A24E'
  if (rate >= 20) return '#E67E22'
  return '#C44D3E'
}

function shortBuildingName(name) {
  const match = name.match(/\d+号楼/)
  return match ? match[0] : name
}

// Animated counters
const animatedValues = ref({})
watch(() => store.data, (newData) => {
  if (!newData) return
  const targets = {
    total: newData.total_elders,
    a: newData.level_a,
    b: newData.level_b,
    c: newData.level_c,
    active: newData.today_active_count,
    rate: newData.today_active_rate,
  }
  Object.entries(targets).forEach(([key, target]) => {
    animateValue(key, target)
  })
}, { immediate: true })

function animateValue(key, target) {
  const steps = 30
  const increment = target / steps
  let current = 0
  const interval = setInterval(() => {
    current += increment
    if (current >= target) {
      current = target
      clearInterval(interval)
    }
    animatedValues.value = {
      ...animatedValues.value,
      [key]: Number.isInteger(target) ? Math.round(current) : Number(current.toFixed(1))
    }
  }, 800 / steps)
}

const areas = computed(() => store.data?.areas || [])
const currentArea = computed(() => areas.value.find(a => a.name === store.activeArea))

function areaElderCount(area) {
  return area.buildings.reduce((sum, b) => sum + b.elder_count, 0)
}

const totalElders = computed(() => store.data?.total_elders || 0)
const levelA = computed(() => store.data?.level_a || 0)
const levelB = computed(() => store.data?.level_b || 0)
const levelC = computed(() => store.data?.level_c || 0)
const riskDistribution = computed(() => store.data?.risk_distribution || null)
const trends = computed(() => store.data?.trends || {})
const dailyActiveRates = computed(() => (trends.value.daily_active || []).map(d => d.rate))
const dailyActiveCounts = computed(() => (trends.value.daily_active || []).map(d => d.count))
const dailyAlertNew = computed(() => (trends.value.daily_alerts || []).map(d => d.new))
const buildingTrends = computed(() => trends.value.building_trends || {})

const pendingConfirmCount = computed(() =>
  store.data?.workstation?.pending_confirmations?.length || 0
)

const maxAlert = computed(() => Math.max(...dailyAlertNew.value, 1))

const trendPoints = computed(() => {
  const data = dailyActiveRates.value
  if (data.length < 2) return []
  const min = Math.min(...data) - 5
  const max = Math.max(...data) + 5
  const range = max - min || 1
  return data.map((v, i) => [
    30 + (i / (data.length - 1)) * 205,
    10 + (1 - (v - min) / range) * 80,
  ])
})

const trendLinePoints = computed(() => trendPoints.value.map(p => p.join(',')).join(' '))

const trendFillPoints = computed(() => {
  const pts = trendPoints.value
  if (pts.length < 2) return ''
  return `${pts[0][0]},90 ${trendLinePoints.value} ${pts[pts.length - 1][0]},90`
})

const trendXLabels = computed(() => (trends.value.daily_active || []).map(d => d.date))

const trendYLabels = computed(() => {
  const data = dailyActiveRates.value
  if (data.length < 2) return []
  const max = Math.max(...data) + 5
  const min = Math.min(...data) - 5
  const mid = Math.round((max + min) / 2)
  return [Math.round(max), mid, Math.round(min)]
})

async function handleConfirm(elderId) {
  try {
    await store.confirmActive(elderId)
    ElMessage.success('已确认活跃')
  } catch {
    ElMessage.error('确认失败，请重试')
  }
}
</script>

<style scoped>
.heat-tile-enter {
  animation: tilePopIn 400ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes tilePopIn {
  from { opacity: 0; transform: scale(0.7) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
