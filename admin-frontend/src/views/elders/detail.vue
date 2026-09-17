<template>
  <div>
    <div class="mb-6">
      <button class="inline-flex items-center gap-1 text-sm text-on-surface-variant hover:text-primary transition-colors" @click="$router.back()">
        <span class="material-symbols-outlined text-lg">arrow_back</span>
        <span>返回档案列表</span>
      </button>
    </div>

    <template v-if="store.current">
      <!-- Profile Card -->
      <div class="bg-surface rounded-3xl shadow-sm border border-outline-variant/20 overflow-hidden mb-6">
        <div class="flex items-center gap-5 p-8 bg-gradient-to-r from-surface-container to-surface border-b border-outline-variant/20">
          <div
            :class="[
              'w-16 h-16 rounded-2xl flex items-center justify-center font-headline text-2xl font-bold text-white shrink-0 shadow-md',
              levelClass,
            ]"
          >
            {{ elderName?.charAt(0) || '?' }}
          </div>
          <div class="min-w-0 flex-1">
            <h2 class="font-headline text-2xl font-bold text-on-surface mb-1">{{ elderName }}</h2>
            <div class="flex items-center gap-2 flex-wrap">
              <span :class="['inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold', levelBadge]">
                {{ store.current.elder?.care_level || store.current.care_level }}级
              </span>
              <span class="text-inactive-gray">·</span>
              <span class="text-sm text-on-surface-variant">{{ elderAddress }}</span>
              <template v-if="store.current.today_active !== undefined">
                <span class="text-inactive-gray">·</span>
                <span :class="['inline-flex items-center gap-1 text-xs font-semibold', store.current.today_active ? 'text-secondary' : 'text-inactive-gray']">
                  <span class="w-2 h-2 rounded-full" :class="store.current.today_active ? 'bg-secondary' : 'bg-inactive-gray'"></span>
                  {{ store.current.today_active ? '今日活跃' : '今日未活跃' }}
                </span>
              </template>
            </div>
          </div>
          <!-- 风险徽章 -->
          <div v-if="riskData?.score != null" class="shrink-0 text-center">
            <div
              :class="[
                'w-14 h-14 rounded-xl flex items-center justify-center text-xl font-bold text-white shadow-md',
                riskBgClass,
              ]"
            >
              {{ riskData.score }}
            </div>
            <span class="text-[10px] text-on-surface-variant mt-1 block">{{ riskLevelLabel }}</span>
          </div>
        </div>

        <div class="p-8">
          <dl class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <dt class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">手机号</dt>
              <dd class="text-sm text-on-surface">
                <a v-if="elderPhone" :href="`tel:${elderPhone}`" class="text-primary hover:underline">{{ elderPhone }}</a>
                <span v-else>—</span>
              </dd>
            </div>
            <div>
              <dt class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">紧急联系人</dt>
              <dd class="text-sm text-on-surface">{{ store.current.elder?.emergency_contact?.name || store.current.emergency_contact_name || '—' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">紧急联系电话</dt>
              <dd class="text-sm text-on-surface">
                <a v-if="emergencyPhone" :href="`tel:${emergencyPhone}`" class="text-primary hover:underline">{{ emergencyPhone }}</a>
                <span v-else>—</span>
              </dd>
            </div>
            <div>
              <dt class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">最后活跃</dt>
              <dd class="text-sm text-on-surface">{{ store.current.last_active_at ? formatDateTime(store.current.last_active_at) : '—' }}</dd>
            </div>
            <div class="md:col-span-2">
              <dt class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">健康备注</dt>
              <dd class="text-sm text-on-surface">{{ store.current.elder?.health_notes || store.current.health_notes || '暂无记录' }}</dd>
            </div>
          </dl>
        </div>
      </div>

      <!-- 日活动轨迹 -->
      <DayTrajectory :elder-id="route.params.id" class="mb-6" />

      <!-- 主内容区：时间线 + 风险仪表盘 -->
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div class="lg:col-span-3">
          <ActivityTimeline
            :items="store.timeline"
            :activity-summary="store.current.activity_summary"
            :has-more="store.timelineHasMore"
            @load-more="store.loadMoreTimeline(route.params.id)"
          />
        </div>
        <div class="lg:col-span-2">
          <RiskDashboard
            :risk="riskData"
            :refreshing="riskRefreshing"
            :ai-result="aiResult"
            :ai-loading="aiLoading"
            @refresh="handleRefreshRisk"
            @request-ai="handleRequestAi"
          />

          <!-- 趋势图 -->
          <TrendCharts
            v-if="store.current.activity_summary"
            :summary="store.current.activity_summary"
            class="mt-6"
          />

          <!-- 家人关系卡片 -->
          <div class="mt-6 bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-6">
            <h3 class="font-headline text-lg font-bold text-on-surface mb-4">家人关系</h3>
            <div v-if="store.current.family_relations?.length" class="space-y-3">
              <div
                v-for="rel in store.current.family_relations"
                :key="rel.relation_id"
                class="flex items-center gap-3 py-2 px-3 rounded-lg bg-surface-container/30"
              >
                <span class="material-symbols-outlined text-lg text-on-surface-variant">person</span>
                <div class="min-w-0 flex-1">
                  <span class="text-sm font-semibold text-on-surface">{{ rel.family_member_name || '未知' }}</span>
                  <span class="text-xs text-on-surface-variant ml-2">{{ rel.relation_label || '' }}</span>
                </div>
                <span :class="['text-[10px] font-bold px-2 py-0.5 rounded-full', rel.status === 'active' ? 'bg-secondary/10 text-secondary' : 'bg-outline-variant/30 text-inactive-gray']">
                  {{ rel.status === 'active' ? '已绑定' : '待确认' }}
                </span>
              </div>
            </div>
            <div v-else class="text-center py-6">
              <span class="material-symbols-outlined text-3xl text-inactive-gray">family_restroom</span>
              <p class="text-sm text-inactive-gray mt-2">暂无家人绑定</p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="pageLoading" class="flex items-center justify-center py-20">
      <div class="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
    </div>

    <div v-else class="text-center py-20">
      <span class="material-symbols-outlined text-5xl text-inactive-gray">person_off</span>
      <p class="text-inactive-gray text-sm mt-3">老人档案不存在或已被删除</p>
      <button class="mt-4 px-6 py-2 rounded-xl text-sm font-semibold text-primary hover:bg-primary/10 transition-colors" @click="$router.back()">返回列表</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useEldersStore } from '@/stores/elders'
import { recalculateRisk, getAiAnalysis } from '@/api/community'
import ActivityTimeline from './components/ActivityTimeline.vue'
import RiskDashboard from './components/RiskDashboard.vue'
import DayTrajectory from './components/DayTrajectory.vue'
import TrendCharts from './components/TrendCharts.vue'

const route = useRoute()
const store = useEldersStore()
const pageLoading = ref(false)
const riskRefreshing = ref(false)
const aiResult = ref(null)
const aiLoading = ref(false)

const elderName = computed(() => store.current?.elder?.name || store.current?.elder_name || '')
const elderAddress = computed(() => store.current?.elder?.address || store.current?.address || '未分配地址')
const elderPhone = computed(() => store.current?.elder?.phone || store.current?.elder_phone || '')
const emergencyPhone = computed(() => store.current?.elder?.emergency_contact?.phone || store.current?.emergency_contact_phone || '')
const careLevel = computed(() => store.current?.elder?.care_level || store.current?.care_level)

const levelClass = computed(() => ({
  A: 'bg-primary', B: 'bg-accent', C: 'bg-secondary',
}[careLevel.value] || 'bg-inactive-gray'))

const levelBadge = computed(() => ({
  A: 'bg-primary/10 text-primary',
  B: 'bg-accent/10 text-accent',
  C: 'bg-secondary/10 text-secondary',
}[careLevel.value] || 'bg-surface-container text-on-surface-variant'))

const riskData = computed(() => store.current?.risk || {})

const riskBgClass = computed(() => {
  const level = riskData.value?.level
  return {
    normal: 'bg-secondary', attention: 'bg-accent',
    warning: 'bg-warning', critical: 'bg-primary',
  }[level] || 'bg-inactive-gray'
})

const riskLevelLabel = computed(() => ({
  normal: '正常', attention: '关注', warning: '预警', critical: '高危',
}[riskData.value?.level] || '—'))

onMounted(async () => {
  pageLoading.value = true
  try {
    await store.loadDetail(route.params.id)
    await store.loadTimeline(route.params.id)
  } catch {
    ElMessage.error('加载老人详情失败')
  } finally {
    pageLoading.value = false
  }
})

async function handleRefreshRisk() {
  riskRefreshing.value = true
  try {
    const data = await recalculateRisk(route.params.id)
    if (store.current) {
      store.current.risk = {
        score: data.risk_score,
        level: data.risk_level,
        details: data.risk_details,
        calculated_at: new Date().toISOString(),
      }
    }
  } catch {
    ElMessage.error('风险评分刷新失败')
  } finally {
    riskRefreshing.value = false
  }
}

async function handleRequestAi() {
  aiLoading.value = true
  try {
    aiResult.value = await getAiAnalysis(route.params.id)
  } catch {
    ElMessage.error('AI 分析请求失败')
  } finally {
    aiLoading.value = false
  }
}

function formatDateTime(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
