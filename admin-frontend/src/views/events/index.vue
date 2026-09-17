<template>
  <div>
    <!-- Page Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="font-headline text-2xl font-bold text-on-surface">事件中心</h2>
        <p class="text-on-surface-variant text-sm mt-1">查看和处理社区老人相关事件</p>
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
          手动新增
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 mb-5">
      <select
        v-model="filters.severity"
        @change="store.load(filters)"
        class="bg-surface border border-outline-variant rounded-xl px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all w-40"
      >
        <option value="">严重程度</option>
        <option value="urgent">紧急</option>
        <option value="warning">警告</option>
        <option value="info">信息</option>
      </select>
      <select
        v-model="filters.event_type"
        @change="store.load(filters)"
        class="bg-surface border border-outline-variant rounded-xl px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all w-40"
      >
        <option value="">事件类型</option>
        <option value="fall">跌倒</option>
        <option value="absent">缺勤</option>
        <option value="emergency">紧急</option>
        <option value="visit">探访</option>
        <option value="other">其他</option>
      </select>
      <select
        v-model="filters.is_resolved"
        @change="store.load(filters)"
        class="bg-surface border border-outline-variant rounded-xl px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all w-40"
      >
        <option :value="null">处理状态</option>
        <option :value="false">未处理</option>
        <option :value="true">已处理</option>
      </select>
    </div>

    <!-- Events Table -->
    <div class="bg-surface rounded-2xl border border-outline-variant/20 shadow-sm overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-outline-variant/20">
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">级别</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">类型</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">描述</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">来源</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">状态</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">时间</th>
            <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in store.events" :key="row.id" class="border-b border-outline-variant/10 hover:bg-surface-container/50 transition-colors">
            <td class="px-6 py-4">
              <div :class="['flex items-center gap-2 text-sm font-semibold', severityColor(row.severity)]">
                <span :class="['w-2 h-2 rounded-full', severityDot(row.severity)]"></span>
                {{ severityLabel(row.severity) }}
              </div>
            </td>
            <td class="px-6 py-4 text-sm text-on-surface">{{ typeLabel(row.event_type) }}</td>
            <td class="px-6 py-4 text-sm text-on-surface max-w-xs truncate">{{ row.description || '—' }}</td>
            <td class="px-6 py-4">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant">
                {{ sourceLabel(row.source) }}
              </span>
            </td>
            <td class="px-6 py-4">
              <div :class="['flex items-center gap-1.5 text-sm font-medium', row.is_resolved ? 'text-secondary' : 'text-primary']">
                <span :class="['w-1.5 h-1.5 rounded-full', row.is_resolved ? 'bg-secondary' : 'bg-primary']"></span>
                {{ row.is_resolved ? '已处理' : '待处理' }}
              </div>
            </td>
            <td class="px-6 py-4 text-sm text-on-surface-variant whitespace-nowrap">{{ formatTime(row.created_at) }}</td>
            <td class="px-6 py-4">
              <button
                v-if="!row.is_resolved"
                class="px-4 py-1.5 rounded-xl text-xs font-semibold bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                @click.stop="openResolve(row)"
              >
                处理
              </button>
              <span v-else-if="row.resolution_note" class="text-xs text-on-surface-variant cursor-help max-w-[160px] block truncate" :title="row.resolution_note">
                {{ row.resolution_note }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="store.loading" class="text-center py-16">
        <div class="inline-flex items-center gap-2 text-on-surface-variant">
          <svg class="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
          <span class="text-sm">加载中...</span>
        </div>
      </div>
      <div v-else-if="!store.events.length" class="text-center py-16">
        <span class="material-symbols-outlined text-5xl text-inactive-gray">notifications_active</span>
        <p class="text-inactive-gray text-sm mt-3">暂无事件记录</p>
      </div>
    </div>

    <!-- Resolve Dialog -->
    <div v-if="showResolveDialog" class="fixed inset-0 z-[200] flex items-center justify-center">
      <div class="absolute inset-0 bg-on-surface/40 backdrop-blur-sm" @click="showResolveDialog = false"></div>
      <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg p-0 overflow-hidden animate-fade-in-up">
        <div class="px-6 py-5 border-b border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface">处理事件</h3>
        </div>
        <div class="px-6 py-5 space-y-4">
          <div class="bg-surface-container rounded-xl p-4">
            <p class="text-sm text-on-surface-variant">{{ resolveTarget?.description || '无描述' }}</p>
          </div>
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">处理备注</label>
            <textarea v-model="resolveNote" rows="3" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all resize-none" placeholder="例：已电话联系家属确认安全 / 已上门探访"></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-outline-variant/20 flex justify-end gap-3">
          <button class="px-6 py-2.5 rounded-xl text-sm font-semibold text-on-surface-variant hover:bg-surface-container transition-colors" @click="showResolveDialog = false">取消</button>
          <button :disabled="submitting" :class="['px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-sm transition-colors', submitting ? 'bg-inactive-gray cursor-not-allowed' : 'bg-primary hover:bg-terracotta']" @click="handleResolve">{{ submitting ? '提交中...' : '确认处理' }}</button>
        </div>
      </div>
    </div>

    <!-- Create Dialog -->
    <div v-if="showDialog" class="fixed inset-0 z-[200] flex items-center justify-center">
      <div class="absolute inset-0 bg-on-surface/40 backdrop-blur-sm" @click="showDialog = false"></div>
      <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg p-0 overflow-hidden animate-fade-in-up">
        <div class="px-6 py-5 border-b border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface">新增事件</h3>
        </div>
        <div class="px-6 py-5 space-y-5">
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">老人ID</label>
            <input v-model="form.elder_id" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all" placeholder="UUID" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">事件类型</label>
              <select v-model="form.event_type" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all">
                <option value="fall">跌倒</option>
                <option value="absent">缺勤</option>
                <option value="emergency">紧急</option>
                <option value="visit">探访</option>
                <option value="other">其他</option>
              </select>
            </div>
            <div>
              <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">严重程度</label>
              <select v-model="form.severity" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all">
                <option value="info">信息</option>
                <option value="warning">警告</option>
                <option value="urgent">紧急</option>
              </select>
            </div>
          </div>
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">描述</label>
            <textarea v-model="form.description" rows="3" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all resize-none" placeholder="描述事件详情..."></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-outline-variant/20 flex justify-end gap-3">
          <button class="px-6 py-2.5 rounded-xl text-sm font-semibold text-on-surface-variant hover:bg-surface-container transition-colors" @click="showDialog = false">取消</button>
          <button :disabled="submitting" :class="['px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-sm transition-colors', submitting ? 'bg-inactive-gray cursor-not-allowed' : 'bg-primary hover:bg-terracotta']" @click="handleCreate">{{ submitting ? '提交中...' : '确认创建' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useEventsStore } from '@/stores/events'
import { downloadExport } from '@/api/export'

const store = useEventsStore()
const showDialog = ref(false)
const showResolveDialog = ref(false)
const submitting = ref(false)
const resolveTarget = ref(null)
const resolveNote = ref('')
const filters = reactive({ severity: '', event_type: '', is_resolved: null })
const form = reactive({ elder_id: '', event_type: 'other', severity: 'info', description: '' })

onMounted(() => store.load())

function handleEscape(e) {
  if (e.key === 'Escape') {
    showResolveDialog.value = false
    showDialog.value = false
  }
}
onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))

function handleExport() {
  downloadExport('/community/export/events')
}

function severityLabel(s) {
  return { urgent: '紧急', warning: '警告', info: '信息' }[s] || s
}
function severityColor(s) {
  return { urgent: 'text-primary', warning: 'text-accent', info: 'text-on-surface-variant' }[s] || ''
}
function severityDot(s) {
  return {
    urgent: 'bg-primary shadow-[0_0_0_3px_rgba(196,77,62,0.15)]',
    warning: 'bg-accent shadow-[0_0_0_3px_rgba(212,162,78,0.15)]',
    info: 'bg-inactive-gray shadow-[0_0_0_3px_rgba(143,136,128,0.1)]'
  }[s] || ''
}
function typeLabel(t) {
  return { fall: '跌倒', absent: '缺勤', emergency: '紧急', visit: '探访', other: '其他' }[t] || t
}
function sourceLabel(s) {
  return { canteen: '食堂', alert: '预警', manual: '手动' }[s] || s
}
function formatTime(t) {
  if (!t) return '—'
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function openResolve(row) {
  resolveTarget.value = row
  resolveNote.value = ''
  showResolveDialog.value = true
}

async function handleResolve() {
  if (!resolveTarget.value) return
  submitting.value = true
  try {
    await store.resolve(resolveTarget.value.id, { resolution_note: resolveNote.value || null })
    showResolveDialog.value = false
    resolveTarget.value = null
    ElMessage.success('事件已处理')
  } catch (e) {
    // handled by interceptor
  } finally {
    submitting.value = false
  }
}

async function handleCreate() {
  if (!form.elder_id) {
    ElMessage.warning('请填写老人ID')
    return
  }
  submitting.value = true
  try {
    await store.create(form)
    showDialog.value = false
    form.elder_id = ''
    form.event_type = 'other'
    form.severity = 'info'
    form.description = ''
    ElMessage.success('事件已创建')
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
