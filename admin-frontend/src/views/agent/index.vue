<template>
  <div class="flex flex-col h-[calc(100vh-80px)]">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-outline-variant/20">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
          <span class="material-symbols-outlined text-white">smart_toy</span>
        </div>
        <div>
          <h2 class="font-headline text-lg font-bold text-on-surface">AI 助手</h2>
          <p class="text-xs text-inactive-gray">溪东社区智能查询</p>
        </div>
      </div>
      <button
        v-if="messages.length > 1"
        class="text-xs text-inactive-gray hover:text-primary transition-colors"
        @click="clearChat"
      >
        <span class="material-symbols-outlined text-sm align-middle mr-1">delete</span>
        清空对话
      </button>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto py-6 space-y-4" @click="handleContentClick">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        :class="['flex gap-3', msg.role === 'user' ? 'flex-row-reverse' : '']"
      >
        <!-- Avatar -->
        <div
          :class="[
            'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-white text-sm',
            msg.role === 'user' ? 'bg-primary' : 'bg-on-surface',
          ]"
        >
          <span class="material-symbols-outlined text-sm">
            {{ msg.role === 'user' ? 'person' : 'smart_toy' }}
          </span>
        </div>

        <!-- Bubble -->
        <div
          :class="[
            'max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
            msg.role === 'user'
              ? 'bg-primary text-white rounded-tr-sm'
              : 'bg-surface-container text-on-surface rounded-tl-sm',
          ]"
        >
          <div v-if="msg.role === 'assistant'" v-html="formatContent(msg.content)"></div>
          <div v-else>{{ msg.content }}</div>
        </div>
      </div>

      <!-- Streaming indicator -->
      <div v-if="streaming" class="flex gap-3">
        <div class="w-8 h-8 rounded-lg bg-on-surface flex items-center justify-center shrink-0 text-white text-sm">
          <span class="material-symbols-outlined text-sm">smart_toy</span>
        </div>
        <div class="bg-surface-container rounded-2xl rounded-tl-sm px-4 py-3 text-sm">
          <div v-if="streamBuffer" v-html="formatContent(streamBuffer)"></div>
          <div v-else class="flex items-center gap-2 text-inactive-gray">
            <div class="flex gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-inactive-gray animate-bounce" style="animation-delay: 0s"></span>
              <span class="w-1.5 h-1.5 rounded-full bg-inactive-gray animate-bounce" style="animation-delay: 0.15s"></span>
              <span class="w-1.5 h-1.5 rounded-full bg-inactive-gray animate-bounce" style="animation-delay: 0.3s"></span>
            </div>
            <span v-if="toolName" class="text-xs">正在查询{{ toolName }}...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick actions -->
    <div v-if="messages.length <= 1" class="flex flex-wrap gap-2 pb-3">
      <button
        v-for="q in quickQuestions"
        :key="q"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-container text-on-surface-variant hover:bg-outline-variant/20 transition-colors"
        @click="sendMessage(q)"
      >{{ q }}</button>
    </div>

    <!-- Input -->
    <div class="pt-3 border-t border-outline-variant/20">
      <div class="flex gap-3">
        <input
          ref="inputEl"
          v-model="inputText"
          class="flex-1 px-4 py-3 rounded-xl bg-surface-container border border-outline-variant/20 text-sm text-on-surface placeholder:text-inactive-gray focus:outline-none focus:ring-2 focus:ring-primary/30"
          placeholder="输入问题，例如：今天哪些老人还没活跃？"
          :disabled="streaming"
          @keydown.enter="handleEnter"
        />
        <button
          :class="[
            'px-5 py-3 rounded-xl text-sm font-bold text-white transition-colors',
            streaming || !inputText.trim() ? 'bg-inactive-gray cursor-not-allowed' : 'bg-primary hover:bg-primary/90',
          ]"
          :disabled="streaming || !inputText.trim()"
          @click="sendMessage(inputText)"
        >
          <span class="material-symbols-outlined text-sm">send</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { streamAgentChat } from '@/api/agent'

const router = useRouter()
const messagesContainer = ref(null)
const inputEl = ref(null)
const inputText = ref('')
const streaming = ref(false)
const streamBuffer = ref('')
const toolName = ref('')

const messages = ref([
  {
    role: 'assistant',
    content: '你好！我是溪东社区AI助手「小溪」。你可以问我关于老人状态、活跃情况、告警等问题。',
  },
])

const quickQuestions = [
  '今日未活跃老人？',
  '祥盛家园3号楼情况？',
  '待处理告警有哪些？',
  'A级老人谁需要关注？',
  '本周活跃率趋势如何？',
  '哪些楼栋活跃率最低？',
  '今日食堂出勤情况？',
]

const TOOL_LABELS = {
  query_inactive_elders: '未活跃老人',
  get_building_summary: '楼栋概况',
  get_elder_status: '老人状态',
  get_today_alerts: '今日告警',
  list_unconfirmed_elders: '待确认列表',
  confirm_elder_active: '确认活跃',
  get_weekly_trend: '周趋势',
}

function handleEnter(e) {
  if (!e.shiftKey && inputText.value.trim()) {
    sendMessage(inputText.value)
  }
}

async function sendMessage(text) {
  const content = text.trim()
  if (!content || streaming.value) return

  inputText.value = ''
  messages.value.push({ role: 'user', content })
  scrollToBottom()

  streaming.value = true
  streamBuffer.value = ''
  toolName.value = ''

  const chatMessages = messages.value
    .filter(m => m !== messages.value[0])
    .map(m => ({ role: m.role, content: m.content }))

  try {
    for await (const event of streamAgentChat(chatMessages)) {
      if (event.type === 'text_delta') {
        streamBuffer.value += event.content
        scrollToBottom()
      } else if (event.type === 'tool_use') {
        toolName.value = TOOL_LABELS[event.name] || event.name
      } else if (event.type === 'error') {
        streamBuffer.value += event.content
      } else if (event.type === 'done') {
        break
      }
    }
  } catch (e) {
    streamBuffer.value = `网络错误: ${e.message}`
  }

  if (streamBuffer.value) {
    messages.value.push({ role: 'assistant', content: streamBuffer.value })
  }
  streaming.value = false
  streamBuffer.value = ''
  toolName.value = ''
  scrollToBottom()
  nextTick(() => inputEl.value?.focus())
}

function clearChat() {
  messages.value = [messages.value[0]]
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function formatContent(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(
      /\[\[elder:([\w-]+):(.*?)\]\]/g,
      '<a data-elder-id="$1" class="text-primary font-bold hover:underline cursor-pointer" rel="noopener noreferrer">$2</a>'
    )

  const lines = html.split('\n')
  const result = []
  let inList = false
  for (const line of lines) {
    const bullet = line.match(/^[\s]*[-•]\s+(.*)/)
    const numbered = line.match(/^[\s]*\d+[.)]\s+(.*)/)
    if (bullet || numbered) {
      if (!inList) { result.push('<ul class="list-disc pl-4 my-1">'); inList = true }
      result.push(`<li>${(bullet || numbered)[1]}</li>`)
    } else {
      if (inList) { result.push('</ul>'); inList = false }
      result.push(line ? `${line}<br>` : '<br>')
    }
  }
  if (inList) result.push('</ul>')
  return result.join('').replace(/<br>$/, '')
}

function handleContentClick(e) {
  const el = e.target.closest('[data-elder-id]')
  if (el) {
    e.preventDefault()
    router.push(`/elders/${el.dataset.elderId}`)
  }
}

onMounted(() => inputEl.value?.focus())
</script>
