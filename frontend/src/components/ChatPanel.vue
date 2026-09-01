<template>
  <section class="chat-panel">
    <div ref="listEl" class="message-list">
      <div v-if="!messages.length" class="empty-state">
        <h3>开始一次制度或订单问答</h3>
        <p>
          未登录仅可问制度；登录 tutor/admin 后可查询 ENR 订单。列表型回答会自动渲染为表格。
        </p>
        <div class="empty-actions">
          <button
            v-for="q in starters"
            :key="q"
            type="button"
            class="starter"
            @click="send(q)"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <article
        v-for="(msg, i) in messages"
        :key="i"
        class="message"
        :class="msg.role"
      >
        <div class="meta">
          <span class="who">{{ msg.role === 'user' ? '你' : '助手' }}</span>
          <span v-if="msg.mode" class="mode">{{ msg.mode }}</span>
        </div>
        <div class="bubble" :class="{ error: msg.error }">
          <template v-if="msg.role === 'assistant' && !msg.error && !msg.streaming">
            <template v-if="viewOf(msg).blocks.length">
              <template v-for="(block, bi) in viewOf(msg).blocks" :key="bi">
                <p v-if="block.type === 'text'" class="bubble-text">{{ block.text }}</p>
                <div v-else-if="block.type === 'table'" class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th v-for="(h, hi) in block.headers" :key="hi">{{ h }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, ri) in block.rows" :key="ri">
                        <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </template>
            <p v-else class="bubble-text">{{ displayContent(msg) || '（空回复）' }}</p>
          </template>
          <span v-else class="bubble-text">{{ displayContent(msg) }}</span>
          <span v-if="msg.streaming" class="cursor">〇</span>
          <span v-if="msg.streaming" class="stream-wait">思考中 {{ waitSeconds }}s</span>
        </div>
      </article>

      <p v-if="busy" class="typing">
        <span class="pulse" /> 助手正在思考… 已等待 {{ waitSeconds }} 秒
      </p>
    </div>

    <footer class="composer">
      <div class="composer-box">
        <textarea
          ref="inputEl"
          v-model="input"
          rows="2"
          placeholder="输入问题… Enter 发送，Shift+Enter 换行"
          :disabled="busy"
          @keydown="onKeydown"
        />
        <div class="composer-bar">
          <span class="hint-route">
            {{ routeHint }}
          </span>
          <button
            type="button"
            class="btn-send"
            :disabled="busy || !input.trim()"
            @click="send()"
          >
            发送
          </button>
        </div>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { postChat, postChatStream, getChatHistory } from '../api/client'
import { useSession } from '../composables/useSession'
import { cacheSessionMessages } from '../composables/sessionMessageCache'
import { parseAnswerBlocks } from '../utils/parseAnswerTable'
import { stripMarkdownInline } from '../utils/formatAnswer'

const emit = defineEmits(['session-updated'])

const { getSessionId, touchSession } = useSession()

const messages = ref([])
const input = ref('')
const inputEl = ref(null)
const loading = ref(false)
const streaming = ref(false)
const waitSeconds = ref(0)
const listEl = ref(null)

let waitTimer = null

function focusInput() {
  nextTick(() => {
    const el = inputEl.value
    if (!el || el.disabled) return
    el.focus({ preventScroll: true })
  })
}

function onWindowFocus() {
  focusInput()
}

function onVisibility() {
  if (document.visibilityState === 'visible') focusInput()
}

const busy = computed(() => loading.value || streaming.value)

function startWaitClock() {
  stopWaitClock()
  waitSeconds.value = 0
  waitTimer = setInterval(() => {
    waitSeconds.value += 1
  }, 1000)
}

function stopWaitClock() {
  if (waitTimer) {
    clearInterval(waitTimer)
    waitTimer = null
  }
}

onMounted(() => {
  focusInput()
  window.addEventListener('focus', onWindowFocus)
  document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
  stopWaitClock()
  window.removeEventListener('focus', onWindowFocus)
  document.removeEventListener('visibilitychange', onVisibility)
})

const starters = [
  '开课后退班怎么扣费？',
  'ENR20250801001 什么状态？',
]

const routeHint = computed(() => {
  const t = input.value.trim()
  if (!t) return '制度问题 → 流式 · 含 ENR/订单 → 图编排'
  if (isPurePolicyQuestion(t)) return '即将：SSE 流式（制度）'
  return '即将：非流式图编排（可含工具查单）'
})

function isPurePolicyQuestion(text) {
  if (/ENR\d+/i.test(text)) return false
  if (/(订单|班级|学员|学生|报名|老师|手机号|工单|优惠券|现金券|退款)/.test(text)) {
    return false
  }
  // 「英语班」「数学班」「多少老师」等短问也必须走图/工具
  if (/(班|老师|学员|来源|概况|多少)/.test(text)) return false
  if (/(最贵|最高消费|最高实付|金额最大)/.test(text)) return false
  if (/(退班|退款|试算|能退)/.test(text) && /[A-Z]*R20\d+/i.test(text)) return false
  return /(退班|换班|转班|结转|制度|开课|退费|手续费|买班|扣费)/.test(text)
}

/** 把技术异常收成用户可读短句（兜底；后端也应已映射） */
function friendlyError(raw) {
  const s = String(raw || '')
  const low = s.toLowerCase()
  if (low.includes('insufficient balance') || low.includes('402')) {
    return '模型服务暂时不可用，请稍后再试。'
  }
  if (low.includes('recursion') || low.includes('graphrecursion')) {
    return '这个问题处理步骤过多，请换个更具体的问法再试一次。'
  }
  if (low.includes('timeout') || low.includes('超时')) {
    return '响应超时，请稍后再试。'
  }
  if (low.includes('rate limit') || low.includes('429')) {
    return '请求太频繁，请稍后再试。'
  }
  if (s.startsWith('请求失败：') && (low.includes('error code') || low.includes('traceback'))) {
    return '暂时无法回答，请稍后再试或换个问法。'
  }
  if (s.startsWith('请求失败：')) return s.replace(/^请求失败：/, '') || '暂时无法回答，请稍后再试。'
  return s || '暂时无法回答，请稍后再试。'
}

function displayContent(msg) {
  return stripMarkdownInline(msg.content || '')
}

function viewOf(msg) {
  return parseAnswerBlocks(msg.content || '')
}

async function scrollToBottom() {
  await nextTick()
  if (listEl.value) {
    listEl.value.scrollTop = listEl.value.scrollHeight
  }
}

async function send(questionText) {
  const text = (questionText ?? input.value).trim()
  if (!text || busy.value) return

  const sid = getSessionId()
  const isFirst = messages.value.length === 0
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  if (isFirst) {
    touchSession(sid, text)
    emit('session-updated')
  } else {
    touchSession(sid)
    emit('session-updated')
  }
  loading.value = true
  streaming.value = false
  startWaitClock()
  await scrollToBottom()

  let assistantIndex = -1

  try {
    if (isPurePolicyQuestion(text)) {
      streaming.value = true
      const streamed = await postChatStream(text, sid, (piece) => {
        if (assistantIndex < 0) {
          messages.value.push({
            role: 'assistant',
            content: piece,
            streaming: true,
            mode: 'SSE',
          })
          assistantIndex = messages.value.length - 1
          loading.value = false
        } else {
          messages.value[assistantIndex].content += piece
        }
        scrollToBottom()
      })
      // 流式拼出来的可能丢换行；以服务端落库正文为准（和刷新历史一致）
      let finalContent = streamed || ''
      try {
        const hist = await getChatHistory(sid)
        const lastAsst = [...(hist.messages || [])]
          .reverse()
          .find((m) => m.role === 'assistant')
        if (lastAsst?.content) finalContent = lastAsst.content
      } catch {
        /* 拉历史失败则用本地拼接 */
      }
      if (assistantIndex >= 0) {
        messages.value[assistantIndex] = {
          role: 'assistant',
          content: finalContent || messages.value[assistantIndex].content || '',
          streaming: false,
          mode: 'SSE',
        }
      } else {
        messages.value.push({
          role: 'assistant',
          content: finalContent || '（没有收到回复）',
          error: !finalContent,
          mode: 'SSE',
        })
      }
    } else {
      const data = await postChat(text, sid)
      messages.value.push({
        role: 'assistant',
        content: data.answer || '（空回复）',
        mode: 'Graph',
      })
    }
  } catch (e) {
    const raw = String(e.message || e)
    const errText = friendlyError(raw)
    if (assistantIndex >= 0) {
      const msg = messages.value[assistantIndex]
      msg.content = msg.content ? `${msg.content}\n\n${errText}` : errText
      msg.streaming = false
      msg.error = true
    } else {
      messages.value.push({
        role: 'assistant',
        content: errText,
        error: true,
      })
    }
  } finally {
    if (assistantIndex >= 0 && messages.value[assistantIndex]) {
      messages.value[assistantIndex].streaming = false
    }
    loading.value = false
    streaming.value = false
    stopWaitClock()
    cacheSessionMessages(sid, messages.value)
    await scrollToBottom()
    focusInput()
  }
}

function clearMessages() {
  messages.value = []
  focusInput()
}

function setMessages(list) {
  messages.value = (list || []).map((m) => ({
    role: m.role,
    content: m.content || '',
  }))
  scrollToBottom()
  focusInput()
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

defineExpose({ send, clearMessages, setMessages })
</script>

<style scoped>
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-panel);
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  min-height: 320px;
}

.empty-state {
  max-width: 520px;
  margin: 48px auto;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
}

.empty-state p {
  margin: 10px 0 20px;
  color: var(--text-muted);
  font-size: 0.88rem;
  line-height: 1.5;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.starter {
  border: 1px solid var(--border);
  background: #f8fafc;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 0.8rem;
  color: var(--text);
}

.starter:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
}

.message {
  margin-bottom: 22px;
  max-width: 720px;
}

.message.user {
  margin-left: auto;
}

.message.assistant {
  margin-right: auto;
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.message.user .meta {
  justify-content: flex-end;
}

.who {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.04em;
}

.mode {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid var(--border-soft);
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  word-break: break-word;
  line-height: 1.55;
  font-size: 0.92rem;
}

.message.user .bubble {
  background: var(--user-bubble);
  color: #ecfdf5;
  border-bottom-right-radius: 4px;
}

.message.assistant .bubble {
  background: #f8fafc;
  border: 1px solid var(--border-soft);
  border-bottom-left-radius: 4px;
  color: var(--text);
}

.bubble.error {
  background: var(--danger-bg);
  border-color: #fecaca;
  color: var(--danger);
}

.bubble-text {
  margin: 0;
  white-space: pre-wrap;
}

.bubble-text + .table-wrap,
.table-wrap + .bubble-text,
.table-wrap + .table-wrap {
  margin-top: 10px;
}

.cursor {
  display: inline-block;
  margin-left: 2px;
  animation: blink 1s step-end infinite;
  color: var(--text-faint);
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.table-wrap {
  margin-top: 10px;
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.table-wrap table {
  border-collapse: collapse;
  width: 100%;
  font-size: 0.82rem;
  background: #fff;
}

.table-wrap th,
.table-wrap td {
  border-bottom: 1px solid var(--border-soft);
  padding: 8px 12px;
  text-align: left;
  vertical-align: top;
}

.table-wrap th {
  background: #f1f5f9;
  font-weight: 600;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.table-wrap tr:last-child td {
  border-bottom: none;
}

.typing {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.stream-wait {
  display: inline-block;
  margin-left: 8px;
  font-size: 0.72rem;
  font-family: var(--font-mono);
  color: var(--text-faint);
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.9);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
}

.composer {
  padding: 16px 20px 20px;
  border-top: 1px solid var(--border-soft);
  background: linear-gradient(180deg, #fafbfc, #fff);
}

.composer-box {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-composer);
  overflow: hidden;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.composer-box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}

.composer textarea {
  width: 100%;
  border: none;
  resize: none;
  padding: 14px 16px 8px;
  outline: none;
  background: transparent;
  color: var(--text);
  min-height: 56px;
}

.composer-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 12px 12px;
}

.hint-route {
  font-size: 0.72rem;
  color: var(--text-faint);
  font-family: var(--font-mono);
}

.btn-send {
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  background: var(--accent);
  color: #fff;
  font-weight: 500;
  font-size: 0.85rem;
}

.btn-send:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
