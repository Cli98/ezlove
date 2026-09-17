<template>
  <div>
    <!-- Page Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="font-headline text-2xl font-bold text-on-surface">邻里帮</h2>
        <p class="text-on-surface-variant text-sm mt-1">志愿者与积分任务管理</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          v-if="activeTab === 'tasks'"
          class="flex items-center gap-2 bg-primary text-white rounded-full px-6 py-2.5 font-semibold text-sm shadow-lg shadow-primary/20 hover:bg-terracotta hover:shadow-xl hover:-translate-y-0.5 active:scale-95 transition-all duration-200"
          @click="showDialog = true"
        >
          <span class="material-symbols-outlined text-lg">add</span>
          发布任务
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center">
            <span class="material-symbols-outlined text-secondary">group</span>
          </div>
          <div>
            <p class="text-2xl font-bold text-on-surface">{{ store.volunteers.length }}</p>
            <p class="text-xs text-on-surface-variant">志愿者</p>
          </div>
        </div>
      </div>
      <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
            <span class="material-symbols-outlined text-accent">assignment</span>
          </div>
          <div>
            <p class="text-2xl font-bold text-on-surface">{{ activeTasks }}</p>
            <p class="text-xs text-on-surface-variant">进行中</p>
          </div>
        </div>
      </div>
      <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <span class="material-symbols-outlined text-primary">check_circle</span>
          </div>
          <div>
            <p class="text-2xl font-bold text-on-surface">{{ verifiedTasks }}</p>
            <p class="text-xs text-on-surface-variant">已完成</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-5 bg-surface-container rounded-xl p-1 w-fit">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="[
          'px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-200',
          activeTab === tab.key
            ? 'bg-white text-on-surface shadow-sm'
            : 'text-on-surface-variant hover:text-on-surface'
        ]"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 任务管理 Tab -->
    <div v-if="activeTab === 'tasks'">
      <!-- Filters -->
      <div class="flex gap-3 mb-5">
        <select
          v-model="taskFilters.status"
          @change="store.loadTasks(cleanFilters)"
          class="bg-surface border border-outline-variant rounded-xl px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all w-40"
        >
          <option value="">全部状态</option>
          <option value="pending">待接取</option>
          <option value="accepted">进行中</option>
          <option value="completed">待审核</option>
          <option value="verified">已完成</option>
        </select>
        <select
          v-model="taskFilters.task_type"
          @change="store.loadTasks(cleanFilters)"
          class="bg-surface border border-outline-variant rounded-xl px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all w-40"
        >
          <option value="">全部类型</option>
          <option value="visit">探访</option>
          <option value="accompany">陪伴</option>
          <option value="check_in">签到</option>
          <option value="errand">代办</option>
        </select>
      </div>

      <div class="bg-surface rounded-2xl border border-outline-variant/20 shadow-sm overflow-hidden">
        <table class="w-full">
          <thead>
            <tr class="border-b border-outline-variant/20">
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">任务标题</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">类型</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">积分</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">志愿者</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">状态</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">创建时间</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in store.tasks" :key="task.id" class="border-b border-outline-variant/10 hover:bg-surface-container/50 transition-colors">
              <td class="px-6 py-4 text-sm text-on-surface font-medium">{{ task.title }}</td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant">
                  {{ taskTypeLabel(task.task_type) }}
                </span>
              </td>
              <td class="px-6 py-4">
                <span class="text-sm font-semibold text-accent">+{{ task.point_value }}</span>
              </td>
              <td class="px-6 py-4 text-sm text-on-surface">{{ task.volunteer_name || '—' }}</td>
              <td class="px-6 py-4">
                <div :class="['flex items-center gap-1.5 text-sm font-medium', statusColor(task.status)]">
                  <span :class="['w-1.5 h-1.5 rounded-full', statusDot(task.status)]"></span>
                  {{ statusLabel(task.status) }}
                </div>
              </td>
              <td class="px-6 py-4 text-sm text-on-surface-variant whitespace-nowrap">{{ formatTime(task.created_at) }}</td>
              <td class="px-6 py-4">
                <button
                  v-if="task.status === 'completed'"
                  class="px-4 py-1.5 rounded-xl text-xs font-semibold bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                  @click="handleVerify(task)"
                >
                  审核通过
                </button>
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
        <div v-else-if="!store.tasks.length" class="text-center py-16">
          <span class="material-symbols-outlined text-5xl text-inactive-gray">assignment</span>
          <p class="text-inactive-gray text-sm mt-3">暂无任务记录</p>
        </div>
      </div>
    </div>

    <!-- 志愿者名单 Tab -->
    <div v-if="activeTab === 'volunteers'">
      <div class="bg-surface rounded-2xl border border-outline-variant/20 shadow-sm overflow-hidden">
        <table class="w-full">
          <thead>
            <tr class="border-b border-outline-variant/20">
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">姓名</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">累计积分</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">可用积分</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">状态</th>
              <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">注册时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="vol in store.volunteers" :key="vol.id" class="border-b border-outline-variant/10 hover:bg-surface-container/50 transition-colors">
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-secondary/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-secondary text-sm">person</span>
                  </div>
                  <span class="text-sm font-medium text-on-surface">{{ vol.elder_name }}</span>
                </div>
              </td>
              <td class="px-6 py-4">
                <span class="text-sm font-semibold text-accent">{{ vol.total_points }}</span>
              </td>
              <td class="px-6 py-4 text-sm text-on-surface">{{ vol.available_points }}</td>
              <td class="px-6 py-4">
                <div :class="['flex items-center gap-1.5 text-sm font-medium', vol.is_active ? 'text-secondary' : 'text-on-surface-variant']">
                  <span :class="['w-1.5 h-1.5 rounded-full', vol.is_active ? 'bg-secondary' : 'bg-inactive-gray']"></span>
                  {{ vol.is_active ? '活跃' : '未活跃' }}
                </div>
              </td>
              <td class="px-6 py-4 text-sm text-on-surface-variant whitespace-nowrap">{{ formatTime(vol.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="store.loading" class="text-center py-16">
          <div class="inline-flex items-center gap-2 text-on-surface-variant">
            <svg class="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
            <span class="text-sm">加载中...</span>
          </div>
        </div>
        <div v-else-if="!store.volunteers.length" class="text-center py-16">
          <span class="material-symbols-outlined text-5xl text-inactive-gray">group</span>
          <p class="text-inactive-gray text-sm mt-3">暂无志愿者</p>
        </div>
      </div>
    </div>

    <!-- 积分排行 Tab -->
    <div v-if="activeTab === 'leaderboard'">
      <div class="bg-surface rounded-2xl border border-outline-variant/20 shadow-sm overflow-hidden">
        <div class="divide-y divide-outline-variant/10">
          <div
            v-for="(entry, index) in store.leaderboard"
            :key="entry.volunteer_id"
            class="flex items-center gap-4 px-6 py-4 hover:bg-surface-container/50 transition-colors"
          >
            <!-- 排名 -->
            <div class="w-10 flex justify-center">
              <span v-if="index === 0" class="material-symbols-outlined text-2xl" style="color: #FFD700">emoji_events</span>
              <span v-else-if="index === 1" class="material-symbols-outlined text-2xl" style="color: #C0C0C0">emoji_events</span>
              <span v-else-if="index === 2" class="material-symbols-outlined text-2xl" style="color: #CD7F32">emoji_events</span>
              <span v-else class="text-lg font-bold text-on-surface-variant">{{ index + 1 }}</span>
            </div>
            <!-- 信息 -->
            <div class="flex items-center gap-3 flex-1">
              <div :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                index < 3 ? 'bg-accent/10' : 'bg-surface-container'
              ]">
                <span :class="['material-symbols-outlined', index < 3 ? 'text-accent' : 'text-on-surface-variant']">person</span>
              </div>
              <div>
                <p class="text-sm font-semibold text-on-surface">{{ entry.elder_name }}</p>
                <p class="text-xs text-on-surface-variant">完成 {{ entry.task_count }} 个任务</p>
              </div>
            </div>
            <!-- 积分 -->
            <div class="text-right">
              <p class="text-lg font-bold text-accent">{{ entry.total_points }}</p>
              <p class="text-xs text-on-surface-variant">积分</p>
            </div>
          </div>
        </div>
        <div v-if="store.loading" class="text-center py-16">
          <div class="inline-flex items-center gap-2 text-on-surface-variant">
            <svg class="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
            <span class="text-sm">加载中...</span>
          </div>
        </div>
        <div v-else-if="!store.leaderboard.length" class="text-center py-16">
          <span class="material-symbols-outlined text-5xl text-inactive-gray">leaderboard</span>
          <p class="text-inactive-gray text-sm mt-3">暂无排行数据</p>
        </div>
      </div>
    </div>

    <!-- Create Task Dialog -->
    <div v-if="showDialog" class="fixed inset-0 z-[200] flex items-center justify-center">
      <div class="absolute inset-0 bg-on-surface/40 backdrop-blur-sm" @click="showDialog = false"></div>
      <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg p-0 overflow-hidden animate-fade-in-up">
        <div class="px-6 py-5 border-b border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface">发布任务</h3>
        </div>
        <div class="px-6 py-5 space-y-5">
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">任务标题</label>
            <input v-model="form.title" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all" placeholder="例：探访王奶奶" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">任务类型</label>
              <select v-model="form.task_type" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all">
                <option value="visit">探访</option>
                <option value="accompany">陪伴</option>
                <option value="check_in">签到</option>
                <option value="errand">代办</option>
              </select>
            </div>
            <div>
              <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">积分奖励</label>
              <input v-model.number="form.point_value" type="number" min="1" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all" placeholder="10" />
            </div>
          </div>
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">任务描述</label>
            <textarea v-model="form.notes" rows="3" class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all resize-none" placeholder="描述任务详情..."></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-outline-variant/20 flex justify-end gap-3">
          <button class="px-6 py-2.5 rounded-xl text-sm font-semibold text-on-surface-variant hover:bg-surface-container transition-colors" @click="showDialog = false">取消</button>
          <button :disabled="submitting" :class="['px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-sm transition-colors', submitting ? 'bg-inactive-gray cursor-not-allowed' : 'bg-primary hover:bg-terracotta']" @click="handleCreate">{{ submitting ? '提交中...' : '确认发布' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useVolunteerStore } from '@/stores/volunteer'

const store = useVolunteerStore()
const activeTab = ref('tasks')
const showDialog = ref(false)
const submitting = ref(false)
const taskFilters = reactive({ status: '', task_type: '' })
const form = reactive({ title: '', task_type: 'visit', point_value: 10, notes: '' })

const tabs = [
  { key: 'tasks', label: '任务管理' },
  { key: 'volunteers', label: '志愿者名单' },
  { key: 'leaderboard', label: '积分排行' },
]

const cleanFilters = computed(() => {
  const f = {}
  if (taskFilters.status) f.status = taskFilters.status
  if (taskFilters.task_type) f.task_type = taskFilters.task_type
  return f
})

const activeTasks = computed(() => store.tasks.filter(t => t.status === 'accepted' || t.status === 'pending').length)
const verifiedTasks = computed(() => store.tasks.filter(t => t.status === 'verified').length)

onMounted(() => {
  store.loadTasks()
  store.loadVolunteers()
})

function switchTab(key) {
  activeTab.value = key
  if (key === 'tasks') store.loadTasks()
  else if (key === 'volunteers') store.loadVolunteers()
  else if (key === 'leaderboard') store.loadLeaderboard()
}

function taskTypeLabel(t) {
  return { visit: '探访', accompany: '陪伴', check_in: '签到', errand: '代办' }[t] || t
}

function statusLabel(s) {
  return { pending: '待接取', accepted: '进行中', completed: '待审核', verified: '已完成' }[s] || s
}

function statusColor(s) {
  return {
    pending: 'text-on-surface-variant',
    accepted: 'text-accent',
    completed: 'text-warning',
    verified: 'text-secondary',
  }[s] || ''
}

function statusDot(s) {
  return {
    pending: 'bg-inactive-gray',
    accepted: 'bg-accent',
    completed: 'bg-warning',
    verified: 'bg-secondary',
  }[s] || ''
}

function formatTime(t) {
  if (!t) return '—'
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function handleVerify(task) {
  try {
    await ElMessageBox.confirm(
      `将发放 ${task.point_value} 积分给志愿者`,
      `确认审核通过「${task.title}」？`,
      { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'success' }
    )
  } catch {
    return
  }
  try {
    await store.verify(task.id)
    ElMessage.success('审核通过，积分已发放')
  } catch (e) {
    // handled by interceptor
  }
}

async function handleCreate() {
  if (!form.title) {
    ElMessage.warning('请填写任务标题')
    return
  }
  submitting.value = true
  try {
    await store.create(form)
    showDialog.value = false
    form.title = ''
    form.task_type = 'visit'
    form.point_value = 10
    form.notes = ''
    ElMessage.success('任务已发布')
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
