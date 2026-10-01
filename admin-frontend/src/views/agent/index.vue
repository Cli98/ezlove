<template>
  <div class="agent-page">
    <PageTopbar
      v-model:search="topSearch"
      :worker-name="userStore.worker?.name || '社工'"
      :pending-events="dashboardStore.data?.pending_events || 0"
      @events="router.push('/events')"
      @search="goToElders"
    />

    <main class="agent-stage">
      <header class="agent-heading">
        <h1>AI 助手</h1>
        <p>把日常信号整理成可执行的关怀建议</p>
      </header>

      <img
        :class="['agent-art', { 'agent-art--chatting': hasConversation }]"
        src="@/assets/ai/assistant-park-elders.png"
        alt="两位老人在社区公园散步的水彩插画"
      />

      <section v-if="!hasConversation" class="agent-suggestions" aria-labelledby="suggestion-title">
        <h2 id="suggestion-title">推荐问题</h2>
        <button
          v-for="(question, index) in quickQuestions"
          :key="question"
          type="button"
          :disabled="streaming"
          :style="{ animationDelay: `${80 + index * 100}ms` }"
          @click="sendMessage(question)"
        >
          <DashboardIcon name="sparkle" />
          <span>{{ question }}</span>
        </button>
      </section>

      <section
        v-else
        ref="messagesContainer"
        class="agent-conversation"
        aria-live="polite"
        @click="handleContentClick"
      >
        <div class="agent-conversation__toolbar">
          <span>关怀建议</span>
          <AppButton variant="ghost" size="xs" @click="clearChat">
            <span class="material-symbols-outlined">delete</span>清空对话
          </AppButton>
        </div>

        <article
          v-for="(message, index) in messages"
          :key="`${message.role}-${index}`"
          :class="['agent-message', `agent-message--${message.role}`]"
        >
          <span class="agent-message__avatar">
            <DashboardIcon v-if="message.role === 'assistant'" name="sparkle" />
            <span v-else class="material-symbols-outlined">person</span>
          </span>
          <div class="agent-message__bubble">
            <div v-if="message.role === 'assistant'" v-html="formatContent(message.content)"></div>
            <div v-else>{{ message.content }}</div>
          </div>
        </article>

        <article v-if="streaming" class="agent-message agent-message--assistant">
          <span class="agent-message__avatar"><DashboardIcon name="sparkle" /></span>
          <div class="agent-message__bubble">
            <div v-if="streamBuffer" v-html="formatContent(streamBuffer)"></div>
            <div v-else class="agent-thinking">
              <span><i></i><i></i><i></i></span>
              {{ toolName ? `正在查询${toolName}…` : '正在整理关怀建议…' }}
            </div>
          </div>
        </article>
      </section>
    </main>

    <AppPanel class="agent-composer">
      <DashboardIcon name="sparkle" />
      <div class="agent-composer__field">
        <input
          ref="inputEl"
          v-model="inputText"
          type="text"
          :placeholder="animatedPlaceholder"
          :disabled="streaming"
          @keydown.enter="handleEnter"
        />
        <AppButton :disabled="streaming" @click="sendMessage(inputText)">
          {{ streaming ? '整理中…' : '问 AI' }}
        </AppButton>
      </div>
    </AppPanel>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { streamAgentChat } from '@/api/agent'
import { useDashboardStore } from '@/stores/dashboard'
import { useUserStore } from '@/stores/user'
import AppButton from '@/components/AppButton.vue'
import AppPanel from '@/components/AppPanel.vue'
import DashboardIcon from '@/components/DashboardIcon.vue'
import PageTopbar from '@/components/PageTopbar.vue'

const router = useRouter()
const userStore = useUserStore()
const dashboardStore = useDashboardStore()
const messagesContainer = ref(null)
const inputEl = ref(null)
const inputText = ref('')
const topSearch = ref('')
const messages = ref([])
const streaming = ref(false)
const streamBuffer = ref('')
const toolName = ref('')
const placeholderText = '输入问题，例如：谁需要优先联系？'
const animatedPlaceholder = ref(placeholderText)
const hasConversation = computed(() => messages.value.length > 0 || streaming.value)
let placeholderInterval
let typingTimer

const quickQuestions = [
  '今天有哪些老人需要优先联系？',
  '帮我总结东苑片区近 7 天情况',
  '张建国最近的信号如何？',
]

const TOOL_LABELS = {
  query_inactive_elders: '未活跃老人',
  get_building_summary: '楼栋概况',
  get_elder_status: '老人状态',
  get_today_alerts: '今日关怀事项',
  list_unconfirmed_elders: '待确认列表',
  confirm_elder_active: '确认活动',
  get_weekly_trend: '近七日情况',
}

onMounted(() => {
  if (!dashboardStore.data) dashboardStore.load()
  inputEl.value?.focus()
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    runPlaceholderTyping()
    placeholderInterval = window.setInterval(runPlaceholderTyping, 30000)
  }
})

onUnmounted(() => {
  window.clearInterval(placeholderInterval)
  window.clearTimeout(typingTimer)
})

function runPlaceholderTyping() {
  window.clearTimeout(typingTimer)
  animatedPlaceholder.value = ''
  let index = 0
  const typeNext = () => {
    animatedPlaceholder.value = placeholderText.slice(0, ++index)
    if (index < placeholderText.length) typingTimer = window.setTimeout(typeNext, 65)
  }
  typingTimer = window.setTimeout(typeNext, 220)
}

function goToElders() {
  router.push({ path: '/elders', query: topSearch.value ? { search: topSearch.value } : {} })
}

function handleEnter(event) {
  if (!event.shiftKey) sendMessage(inputText.value)
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

  try {
    for await (const event of streamAgentChat(messages.value.map(message => ({ role: message.role, content: message.content })))) {
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
  } catch (error) {
    streamBuffer.value = `暂时无法连接 AI 助手：${error.message}`
  }

  if (streamBuffer.value) messages.value.push({ role: 'assistant', content: streamBuffer.value })
  streaming.value = false
  streamBuffer.value = ''
  toolName.value = ''
  scrollToBottom()
  nextTick(() => inputEl.value?.focus())
}

function clearChat() {
  messages.value = []
  nextTick(() => inputEl.value?.focus())
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  })
}

function formatContent(text) {
  if (!text) return ''
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(
      /\[\[elder:([\w-]+):(.*?)\]\]/g,
      '<a data-elder-id="$1" class="agent-elder-link" rel="noopener noreferrer">$2</a>'
    )

  const result = []
  let inList = false
  for (const line of escaped.split('\n')) {
    const item = line.match(/^[\s]*(?:[-•]|\d+[.)])\s+(.*)/)
    if (item) {
      if (!inList) result.push('<ul>')
      inList = true
      result.push(`<li>${item[1]}</li>`)
    } else {
      if (inList) result.push('</ul>')
      inList = false
      result.push(line ? `${line}<br>` : '<br>')
    }
  }
  if (inList) result.push('</ul>')
  return result.join('').replace(/<br>$/, '')
}

function handleContentClick(event) {
  const elderLink = event.target.closest('[data-elder-id]')
  if (!elderLink) return
  event.preventDefault()
  router.push(`/elders/${elderLink.dataset.elderId}`)
}
</script>

<style scoped>
.agent-page {
  position: relative;
  display: grid;
  height: 100%;
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}
.agent-page::after {
  position: absolute;
  right: -80px;
  bottom: -105px;
  width: 480px;
  height: 270px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(215, 156, 116, .08), transparent 68%);
  content: '';
  pointer-events: none;
}
.agent-stage { position: relative; min-height: 0; overflow: hidden; }
.agent-heading { position: relative; z-index: 2; padding: 16px 8px 0; }
.agent-heading h1 {
  margin: 0;
  color: #1d2c43;
  font: 900 34px/1.18 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  letter-spacing: .02em;
  transform: scaleX(.94);
  transform-origin: left center;
}
.agent-heading p { margin: 7px 0 0; color: #65738a; font-size: 16px; letter-spacing: .02em; }
.agent-art {
  position: absolute;
  z-index: 0;
  top: 28px;
  right: -12px;
  width: min(760px, 60vw);
  max-height: 400px;
  object-fit: contain;
  object-position: right top;
  opacity: .76;
  pointer-events: none;
  transition: opacity .25s ease;
}
.agent-art--chatting { opacity: .11; }
.agent-suggestions { position: relative; z-index: 2; width: min(570px, 47vw); margin: 116px 0 0 36px; }
.agent-suggestions h2 {
  margin: 0 0 20px;
  color: #263145;
  font: 900 20px/1.2 'Songti SC', 'STSong', 'Noto Serif SC', serif;
}
.agent-suggestions button {
  display: flex;
  width: 100%;
  min-height: 64px;
  align-items: center;
  gap: 20px;
  padding: 0;
  border: 0;
  color: #30333a;
  background: transparent;
  font-size: 16px;
  text-align: left;
  cursor: pointer;
  transition: color .18s ease, transform .18s ease;
  animation: suggestion-pop .62s cubic-bezier(.2, .8, .25, 1) both;
}
.agent-suggestions button:hover { color: #c6533d; transform: translateX(4px); }
.agent-suggestions button:disabled { opacity: .55; cursor: default; }
.agent-suggestions button :deep(.dashboard-icon) { color: #cf5a43; font-size: 28px; stroke-width: 1.55; }
.agent-conversation {
  position: relative;
  z-index: 2;
  width: min(900px, calc(100% - 72px));
  height: calc(100% - 104px);
  margin: 24px auto 0;
  padding: 0 14px 26px;
  overflow-y: auto;
}
.agent-conversation__toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; color: #27344a; }
.agent-conversation__toolbar > span { font: 900 20px/1.2 'Songti SC', 'STSong', serif; }
.agent-message { display: flex; align-items: flex-start; gap: 12px; margin: 0 0 18px; }
.agent-message--user { flex-direction: row-reverse; }
.agent-message__avatar {
  display: grid;
  width: 34px;
  height: 34px;
  flex: none;
  place-items: center;
  border-radius: 10px;
  color: #fff;
  background: #c6533d;
}
.agent-message--assistant .agent-message__avatar { color: #c6533d; border: 1px solid #ebd6cd; background: #fffaf6; }
.agent-message__avatar :deep(.dashboard-icon), .agent-message__avatar .material-symbols-outlined { font-size: 19px; }
.agent-message__bubble {
  max-width: min(74%, 680px);
  padding: 13px 16px;
  border: 1px solid #e7ded6;
  border-radius: 4px 15px 15px;
  color: #354157;
  background: rgba(255, 255, 255, .9);
  box-shadow: 0 4px 14px rgba(65, 49, 36, .04);
  font-size: 14px;
  line-height: 1.85;
}
.agent-message--user .agent-message__bubble { color: #fff; border-color: #c6533d; border-radius: 15px 4px 15px 15px; background: #c6533d; }
.agent-message__bubble :deep(ul) { margin: 4px 0; padding-left: 20px; }
.agent-message__bubble :deep(.agent-elder-link) { color: #c6533d; font-weight: 700; text-decoration: underline; cursor: pointer; }
.agent-thinking { display: flex; align-items: center; gap: 10px; color: #7c818a; }
.agent-thinking > span { display: flex; gap: 4px; }
.agent-thinking i { width: 5px; height: 5px; border-radius: 50%; background: #c6533d; animation: agent-bounce 1s infinite ease-in-out; }
.agent-thinking i:nth-child(2) { animation-delay: .15s; }.agent-thinking i:nth-child(3) { animation-delay: .3s; }
.agent-composer {
  position: relative;
  z-index: 3;
  display: flex;
  min-height: 94px;
  align-items: center;
  gap: 18px;
  margin: 0 20px 0 34px;
  padding: 14px 18px;
  border-color: rgba(198, 83, 61, .25);
  background: rgba(255, 250, 246, .82);
}
.agent-composer > :deep(.dashboard-icon) { color: #c6533d; font-size: 36px; stroke-width: 1.55; }
.agent-composer__field {
  display: flex;
  height: 56px;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 12px;
  padding: 3px 4px 3px 18px;
  border: 1px solid #ddd7d2;
  border-radius: 8px;
  background: rgba(255, 255, 255, .92);
  box-shadow: inset 0 1px 2px rgba(52, 43, 36, .02);
}
.agent-composer__field:focus-within { border-color: rgba(198, 83, 61, .55); box-shadow: 0 0 0 3px rgba(198, 83, 61, .08); }
.agent-composer input { min-width: 0; flex: 1; border: 0; outline: 0; color: #2f3540; background: transparent; font-size: 14px; }
.agent-composer input::placeholder { color: #9b9da4; }
.agent-composer input:disabled { cursor: wait; }
.agent-composer :deep(.app-button) { height: 48px; min-width: 106px; border-radius: 7px; font-size: 14px; }
@keyframes agent-bounce { 0%, 60%, 100% { transform: translateY(0); opacity: .45; } 30% { transform: translateY(-4px); opacity: 1; } }
@keyframes suggestion-pop {
  0% { opacity: 0; transform: translateY(18px); }
  62% { opacity: 1; transform: translateY(-6px); }
  100% { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .agent-suggestions button { animation: none; }
}
@media (max-width: 1080px) {
  .agent-art { width: 58vw; opacity: .52; }
  .agent-suggestions { width: 54vw; margin-left: 18px; }
  .agent-composer { margin-left: 18px; }
}
@media (max-height: 720px) {
  .agent-art { max-height: 310px; }
  .agent-suggestions { margin-top: 58px; }
  .agent-suggestions button { min-height: 54px; }
  .agent-composer { min-height: 76px; padding-block: 9px; }
}
</style>
