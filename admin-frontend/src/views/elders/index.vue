<template>
  <div>
    <!-- Page Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="font-headline text-2xl font-bold text-on-surface">老人档案</h2>
        <p class="text-on-surface-variant text-sm mt-1">管理社区老人信息，设置关爱分级</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          class="flex items-center gap-2 bg-surface-container text-on-surface rounded-full px-5 py-2.5 font-semibold text-sm hover:bg-outline-variant/30 transition-all duration-200"
          @click="handleExport"
        >
          <span class="material-symbols-outlined text-lg">download</span>
          导出 Excel
        </button>
        <button
          class="flex items-center gap-2 bg-primary text-white rounded-full px-6 py-2.5 font-semibold text-sm shadow-lg shadow-primary/20 hover:bg-terracotta hover:shadow-xl hover:-translate-y-0.5 active:scale-95 transition-all duration-200"
          @click="showDialog = true"
        >
          <span class="material-symbols-outlined text-lg">add</span>
          新增老人
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 mb-5">
      <select
        v-model="filters.care_level"
        @change="store.load(filters)"
        class="bg-surface border border-outline-variant rounded-xl px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all w-48"
      >
        <option value="">按分级筛选</option>
        <option value="A">A级（需重点关爱）</option>
        <option value="B">B级（独居需关注）</option>
        <option value="C">C级（健康可互助）</option>
      </select>
      <div class="relative">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-lg">search</span>
        <input
          v-model="filters.search"
          @input="debouncedSearch"
          class="bg-surface border border-outline-variant rounded-xl pl-10 pr-4 py-2.5 text-sm text-on-surface placeholder:text-outline-variant/60 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all w-56"
          placeholder="搜索姓名..."
          type="text"
        />
      </div>
    </div>

    <!-- Table -->
    <div class="bg-surface rounded-2xl border border-outline-variant/20 shadow-sm overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-outline-variant/20">
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">姓名</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">分级</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">楼栋/门牌</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">今日状态</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">风险</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">健康备注</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in store.elders"
            :key="row.id"
            class="border-b border-outline-variant/10 hover:bg-surface-container/50 cursor-pointer transition-colors"
            @click="$router.push(`/elders/${row.id}`)"
          >
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div
                  :class="[
                    'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0',
                    row.care_level === 'A' ? 'bg-primary' : row.care_level === 'B' ? 'bg-accent' : 'bg-secondary'
                  ]"
                >
                  {{ row.elder_name?.charAt(0) }}
                </div>
                <span class="text-sm font-medium text-on-surface">{{ row.elder_name }}</span>
              </div>
            </td>
            <td class="px-6 py-4">
              <span
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold',
                  row.care_level === 'A' ? 'bg-primary/10 text-primary' : row.care_level === 'B' ? 'bg-accent/10 text-accent' : 'bg-secondary/10 text-secondary'
                ]"
              >
                {{ row.care_level }}级
              </span>
            </td>
            <td class="px-6 py-4 text-sm text-on-surface">{{ row.address || '—' }}</td>
            <td class="px-6 py-4">
              <div class="flex items-center gap-2 text-sm">
                <span
                  :class="[
                    'w-2 h-2 rounded-full',
                    row.today_active ? 'bg-secondary shadow-[0_0_0_3px_rgba(107,143,113,0.15)]' : 'bg-inactive-gray shadow-[0_0_0_3px_rgba(196,186,176,0.15)]'
                  ]"
                ></span>
                {{ row.today_active ? '活跃' : '未活跃' }}
              </div>
            </td>
            <td class="px-6 py-4">
              <span
                v-if="row.risk_level"
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold',
                  row.risk_level === 'critical' ? 'bg-primary/10 text-primary' :
                  row.risk_level === 'warning' ? 'bg-warning/10 text-warning' :
                  row.risk_level === 'attention' ? 'bg-accent/10 text-accent' :
                  'bg-secondary/10 text-secondary'
                ]"
              >
                {{ { normal: '正常', attention: '关注', warning: '预警', critical: '高危' }[row.risk_level] || '—' }}
                <template v-if="row.risk_score != null"> · {{ row.risk_score }}</template>
              </span>
              <span v-else class="text-xs text-inactive-gray">—</span>
            </td>
            <td class="px-6 py-4 text-sm text-on-surface-variant">{{ row.health_notes || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="store.loading" class="text-center py-16">
        <div class="inline-flex items-center gap-2 text-on-surface-variant">
          <svg class="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
          <span class="text-sm">加载中...</span>
        </div>
      </div>
      <div v-else-if="!store.elders.length" class="text-center py-16">
        <span class="material-symbols-outlined text-5xl text-inactive-gray">groups</span>
        <p class="text-inactive-gray text-sm mt-3">暂无老人数据</p>
      </div>
    </div>

    <!-- Create Dialog -->
    <div v-if="showDialog" class="fixed inset-0 z-[200] flex items-center justify-center">
      <div class="absolute inset-0 bg-on-surface/40 backdrop-blur-sm" @click="showDialog = false"></div>
      <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg p-0 overflow-hidden animate-fade-in-up">
        <div class="px-6 py-5 border-b border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface">新增老人</h3>
        </div>
        <div class="px-6 py-5 space-y-5">
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">老人ID（UUID）</label>
            <input v-model="form.elder_id" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all" placeholder="输入老人的用户ID" />
          </div>
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">关爱分级</label>
            <div class="flex gap-2">
              <button
                v-for="level in ['A', 'B', 'C']"
                :key="level"
                :class="[
                  'flex-1 py-2.5 rounded-xl text-sm font-semibold border transition-all',
                  form.care_level === level
                    ? level === 'A' ? 'bg-primary/10 border-primary text-primary' : level === 'B' ? 'bg-accent/10 border-accent text-accent' : 'bg-secondary/10 border-secondary text-secondary'
                    : 'bg-white border-outline-variant text-on-surface-variant hover:border-outline'
                ]"
                @click="form.care_level = level"
              >
                {{ level }}级{{ level === 'A' ? ' · 重点关爱' : level === 'B' ? ' · 独居关注' : ' · 健康互助' }}
              </button>
            </div>
          </div>
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">楼栋/门牌</label>
            <input v-model="form.address" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all" placeholder="例：1号楼203" />
          </div>
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">健康备注</label>
            <textarea v-model="form.health_notes" rows="3" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all resize-none" placeholder="如：高血压、认知障碍、行动不便等"></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-outline-variant/20 flex justify-end gap-3">
          <button class="px-6 py-2.5 rounded-xl text-sm font-semibold text-on-surface-variant hover:bg-surface-container transition-colors" @click="showDialog = false">取消</button>
          <button :disabled="submitting" :class="['px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-sm transition-colors', submitting ? 'bg-inactive-gray cursor-not-allowed' : 'bg-primary hover:bg-terracotta']" @click="handleCreate">{{ submitting ? '提交中...' : '确认添加' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useEldersStore } from '@/stores/elders'
import { downloadExport } from '@/api/export'

const store = useEldersStore()
const showDialog = ref(false)
const submitting = ref(false)
const filters = reactive({ care_level: '', search: '' })
const form = reactive({ elder_id: '', care_level: 'B', address: '', health_notes: '' })
let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => store.load(filters), 300)
}

onMounted(() => store.load())

function handleEscape(e) {
  if (e.key === 'Escape') showDialog.value = false
}
onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))

function handleExport() {
  downloadExport('/community/export/elders')
}

async function handleCreate() {
  if (!form.elder_id || !form.care_level) {
    ElMessage.warning('请填写必填项')
    return
  }
  submitting.value = true
  try {
    await store.create(form)
    showDialog.value = false
    form.elder_id = ''
    form.care_level = 'B'
    form.address = ''
    form.health_notes = ''
    ElMessage.success('老人档案已创建')
  } catch (e) {
    // handled by interceptor
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.animate-fade-in-up {
  animation: fadeInUp 400ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
