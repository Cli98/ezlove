<template>
  <div>
    <!-- Page Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="font-headline text-2xl font-bold text-on-surface">食堂管理</h2>
        <p class="text-on-surface-variant text-sm mt-1">录入就餐数据，AI 自动解析并生成预警</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          class="flex items-center gap-2 bg-primary text-white rounded-full px-5 py-2.5 font-semibold text-sm hover:bg-terracotta transition-all duration-200 shadow-md shadow-primary/20 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:bg-primary"
          :disabled="store.generating"
          @click="handleGenerateMenu"
        >
          <span class="material-symbols-outlined text-lg" :class="{ 'animate-spin': store.generating }">
            {{ store.generating ? 'progress_activity' : 'restaurant_menu' }}
          </span>
          {{ store.generating ? '生成中...' : '生成今日菜单' }}
        </button>
        <button
          class="flex items-center gap-2 bg-surface-container text-on-surface rounded-full px-5 py-2.5 font-semibold text-sm hover:bg-outline-variant/30 transition-all duration-200"
          @click="handleExport"
        >
          <span class="material-symbols-outlined text-lg">download</span>
          导出出勤
        </button>
      </div>
    </div>

    <div class="flex flex-col gap-6">
      <!-- Menu Empty State -->
      <div v-if="!store.menus.length" class="bg-surface rounded-3xl shadow-sm border border-outline-variant/20 p-12 text-center">
        <span class="material-symbols-outlined text-5xl text-inactive-gray">restaurant_menu</span>
        <p class="text-inactive-gray text-sm mt-3">暂无菜单，点击上方「生成今日菜单」开始</p>
      </div>

      <!-- Menu Card -->
      <div v-if="store.menus.length" class="bg-surface rounded-3xl shadow-sm border border-outline-variant/20 overflow-hidden">
        <div class="px-6 py-5 border-b border-outline-variant/20 flex justify-between items-center">
          <h3 class="font-headline text-lg font-bold text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">restaurant_menu</span>
            菜单管理
          </h3>
          <div class="flex items-center gap-2">
            <select v-model="menuMealType" class="px-3 py-1.5 rounded-lg border border-outline-variant/30 text-sm bg-white text-on-surface">
              <option value="lunch">午餐</option>
              <option value="dinner">晚餐</option>
            </select>
          </div>
        </div>
        <div class="p-6">
          <div v-for="menu in filteredMenus" :key="menu.id" class="mb-6 last:mb-0">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-3">
                <span class="text-sm text-on-surface-variant">{{ menu.menu_date }}</span>
                <span class="text-sm font-medium">{{ menu.meal_type === 'lunch' ? '午餐' : '晚餐' }}</span>
                <span
                  :class="[
                    'px-2.5 py-0.5 rounded-full text-xs font-semibold',
                    menu.status === 'published' ? 'bg-secondary/10 text-secondary' : 'bg-accent/10 text-accent'
                  ]"
                >
                  {{ menu.status === 'published' ? '已发布' : '草稿' }}
                </span>
              </div>
              <div class="flex items-center gap-2">
                <button
                  v-if="menu.status === 'draft'"
                  class="px-4 py-1.5 bg-primary text-white rounded-lg text-sm font-semibold hover:bg-terracotta transition-colors"
                  @click="handlePublish(menu.id)"
                >
                  发布
                </button>
                <button
                  class="px-3 py-1.5 text-on-surface-variant hover:text-primary rounded-lg text-sm transition-colors"
                  @click="handleDeleteMenu(menu.id)"
                >
                  <span class="material-symbols-outlined text-lg">delete</span>
                </button>
              </div>
            </div>

            <!-- Dishes display -->
            <div v-if="menu.dishes" class="space-y-3">
              <div class="grid grid-cols-2 gap-3">
                <div
                  v-for="(dish, di) in (menu.dishes.items || [])"
                  :key="di"
                  class="flex items-start gap-3 p-3 rounded-xl bg-surface-container/50"
                >
                  <span
                    :class="[
                      'w-2 h-2 rounded-full mt-1.5 shrink-0',
                      dish.category === '荤菜' ? 'bg-primary' : 'bg-secondary'
                    ]"
                  />
                  <div>
                    <div class="text-sm font-semibold text-on-surface">{{ dish.name }}</div>
                    <div class="text-xs text-on-surface-variant mt-0.5">{{ dish.description }}</div>
                  </div>
                </div>
              </div>
              <div class="flex flex-wrap gap-4 mt-3 text-sm text-on-surface-variant">
                <div v-if="menu.dishes.soup" class="flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-base text-accent">soup_kitchen</span>
                  {{ menu.dishes.soup }}
                </div>
                <div v-if="menu.dishes.staple" class="flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-base text-accent">rice_bowl</span>
                  {{ menu.dishes.staple }}
                </div>
              </div>
              <div v-if="menu.dishes.summary" class="text-xs text-on-surface-variant italic mt-2 px-1">
                {{ menu.dishes.summary }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Card -->
      <div class="bg-surface rounded-3xl shadow-sm border border-outline-variant/20 overflow-hidden">
        <div class="px-6 py-5 border-b border-outline-variant/20">
          <h3 class="font-headline text-lg font-bold text-on-surface">录入就餐数据</h3>
        </div>
        <div class="p-6 space-y-5">
          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">文本描述</label>
            <textarea
              v-model="rawText"
              rows="4"
              class="w-full px-4 py-3 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all resize-none"
              placeholder="例：今天中午食堂，张大爷来了，李奶奶没来，王大爷来了但没怎么吃"
            ></textarea>
          </div>

          <div>
            <label class="text-sm font-semibold text-charcoal ml-1 block mb-1.5">或上传 Excel 文件</label>
            <div
              class="border-2 border-dashed border-outline-variant rounded-2xl p-8 text-center hover:border-primary/40 transition-colors cursor-pointer"
              @click="$refs.fileInput.click()"
              @dragover.prevent
              @drop.prevent="handleFileDrop"
            >
              <span class="material-symbols-outlined text-4xl text-inactive-gray block mb-2">upload_file</span>
              <div class="text-sm text-on-surface-variant">
                <span>将文件拖拽到此处，或</span>
                <span class="text-primary font-semibold ml-1">点击选择</span>
              </div>
              <p v-if="fileBytes" class="text-xs text-secondary font-semibold mt-2">{{ fileBytes.name }}</p>
            </div>
            <input ref="fileInput" type="file" accept=".xlsx,.xls" class="hidden" @change="handleFileChange" />
          </div>

          <button
            :disabled="store.submitting"
            :class="{ 'opacity-80 cursor-not-allowed': store.submitting }"
            class="w-full py-4 bg-primary text-white font-semibold rounded-xl shadow-lg shadow-primary/20 hover:bg-terracotta hover:shadow-xl transition-all duration-200 flex items-center justify-center gap-2"
            @click="handleSubmit"
          >
            <span class="material-symbols-outlined">auto_awesome</span>
            {{ store.submitting ? '解析中...' : 'AI 解析并提交' }}
          </button>
        </div>
      </div>

      <!-- Parsed Results Card -->
      <div v-if="lastParsed" class="bg-surface rounded-3xl shadow-sm border border-outline-variant/20 overflow-hidden">
        <div class="px-6 py-5 border-b border-outline-variant/20 flex justify-between items-center">
          <h3 class="font-headline text-lg font-bold text-on-surface">解析结果</h3>
          <button class="text-sm text-on-surface-variant hover:text-primary transition-colors" @click="lastParsed = null">关闭</button>
        </div>
        <div class="p-6">
          <div v-if="lastParsed.meal_type" class="text-sm text-on-surface-variant mb-4">
            餐次：<span class="font-semibold text-on-surface">{{ lastParsed.meal_type }}</span>
            · 出席 <span class="font-semibold text-secondary">{{ parsedPresent.length }}</span> 人
            · 缺席 <span class="font-semibold text-primary">{{ parsedAbsent.length }}</span> 人
          </div>
          <!-- Absent list (highlight) -->
          <div v-if="parsedAbsent.length" class="mb-4">
            <div class="text-xs font-bold text-primary uppercase tracking-wider mb-2">未到食堂</div>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="(a, i) in parsedAbsent"
                :key="'abs-' + i"
                :class="[
                  'inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-semibold',
                  a.care_level === 'A' ? 'bg-primary/15 text-primary' : a.care_level === 'B' ? 'bg-accent/15 text-accent' : 'bg-surface-container text-on-surface-variant'
                ]"
              >
                {{ a.name }}
                <span v-if="a.care_level" class="text-xs opacity-70">{{ a.care_level }}</span>
              </span>
            </div>
          </div>
          <!-- Present list -->
          <div v-if="parsedPresent.length">
            <div class="text-xs font-bold text-secondary uppercase tracking-wider mb-2">已到食堂</div>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="(a, i) in parsedPresent"
                :key="'pre-' + i"
                class="inline-flex items-center px-3 py-1.5 rounded-full text-sm bg-secondary/10 text-secondary font-medium"
              >
                {{ a.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- History Card -->
      <div class="bg-surface rounded-3xl shadow-sm border border-outline-variant/20 overflow-hidden">
        <div class="px-6 py-5 border-b border-outline-variant/20 flex justify-between items-center">
          <h3 class="font-headline text-lg font-bold text-on-surface">历史记录</h3>
          <button class="flex items-center gap-1 text-sm text-on-surface-variant hover:text-primary transition-colors" @click="store.load()">
            <span class="material-symbols-outlined text-lg">refresh</span>
            刷新
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-outline-variant/20">
                <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">时间</th>
                <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">来源</th>
                <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">状态</th>
                <th class="text-left px-6 py-4 text-xs font-bold text-on-surface-variant tracking-wider uppercase">原始内容</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in store.records" :key="row.id" :class="['border-b border-outline-variant/10 hover:bg-surface-container/50 transition-colors', row.parse_status === 'success' ? 'cursor-pointer' : '']" @click="row.parse_status === 'success' && row.parsed_data && (lastParsed = row.parsed_data)">
                <td class="px-6 py-4 text-sm text-on-surface-variant whitespace-nowrap">{{ formatTime(row.created_at) }}</td>
                <td class="px-6 py-4">
                  <span
                    :class="[
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold',
                      row.source_format === 'excel' ? 'bg-accent/10 text-accent' : 'bg-surface-container text-on-surface-variant'
                    ]"
                  >
                    {{ row.source_format === 'excel' ? 'Excel' : '文本' }}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <span
                    :class="[
                      'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold',
                      row.parse_status === 'success' ? 'bg-secondary/10 text-secondary' : row.parse_status === 'failed' ? 'bg-primary/10 text-primary' : 'bg-surface-container text-on-surface-variant'
                    ]"
                  >
                    <span class="w-1.5 h-1.5 rounded-full" :class="row.parse_status === 'success' ? 'bg-secondary' : row.parse_status === 'failed' ? 'bg-primary' : 'bg-inactive-gray'"></span>
                    {{ { success: '已解析', failed: '失败', pending: '解析中' }[row.parse_status] || row.parse_status }}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm text-on-surface max-w-xs truncate">{{ row.raw_text || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="store.loading" class="text-center py-12">
            <div class="inline-flex items-center gap-2 text-on-surface-variant">
              <svg class="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
              <span class="text-sm">加载中...</span>
            </div>
          </div>
          <div v-else-if="!store.records.length" class="text-center py-12">
            <span class="material-symbols-outlined text-4xl text-inactive-gray">restaurant</span>
            <p class="text-inactive-gray text-sm mt-2">暂无就餐记录</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useCanteenStore } from '@/stores/canteen'
import { downloadExport } from '@/api/export'

const store = useCanteenStore()
const rawText = ref('')
const fileBytes = ref(null)
const fileInput = ref(null)
const lastParsed = ref(null)
const menuMealType = ref('lunch')

const parsedPresent = computed(() =>
  (lastParsed.value?.attendees || []).filter(a => a.present)
)
const parsedAbsent = computed(() =>
  (lastParsed.value?.attendees || []).filter(a => !a.present)
)
const filteredMenus = computed(() =>
  store.menus.filter(m => m.meal_type === menuMealType.value)
)

onMounted(() => {
  store.load()
  store.loadMenus()
})

function handleExport() {
  downloadExport('/community/export/canteen')
}

async function handleGenerateMenu() {
  try {
    await store.generate(menuMealType.value)
  } catch (e) {
    // handled by store
  }
}

async function handlePublish(id) {
  try {
    await store.publish(id)
  } catch (e) {
    // handled by store
  }
}

async function handleDeleteMenu(id) {
  try {
    await ElMessageBox.confirm('确定删除此菜单？', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await store.remove(id)
    ElMessage.success('菜单已删除')
  } catch (e) {
    // handled by store
  }
}

function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (file) fileBytes.value = file
}

function handleFileDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
    fileBytes.value = file
  }
}

function formatTime(t) {
  if (!t) return '—'
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function handleSubmit() {
  if (!rawText.value && !fileBytes.value) {
    ElMessage.warning('请输入就餐描述或上传 Excel 文件')
    return
  }
  const formData = new FormData()
  if (rawText.value) formData.append('raw_text', rawText.value)
  if (fileBytes.value) formData.append('file', fileBytes.value)

  try {
    const result = await store.submit(formData)
    rawText.value = ''
    fileBytes.value = null
    if (fileInput.value) fileInput.value.value = ''
    if (result?.parsed_data && result.parse_status === 'success') {
      lastParsed.value = result.parsed_data
    }
  } catch (e) {
    // handled by interceptor
  }
}
</script>
