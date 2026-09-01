<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true" />
        <div>
          <div class="brand-name">教培知识助手</div>
          <div class="brand-sub">Enterprise RAG · LangGraph</div>
        </div>
      </div>

      <button type="button" class="btn-new" @click="onNewChat">
        + 新建会话
      </button>

      <div class="nav-block history-block">
        <div class="nav-label">历史会话</div>
        <p v-if="!sessions.length" class="hist-empty">发送消息后会出现在这里</p>
        <button
          v-for="s in sessions"
          :key="s.id"
          type="button"
          class="hist-item"
          :class="{ active: s.id === currentSessionId }"
          @click="openSession(s.id)"
        >
          <span class="hist-title">{{ s.title || '未命名' }}</span>
          <span class="hist-time">{{ formatTime(s.updatedAt) }}</span>
        </button>
      </div>

      <div class="nav-block">
        <div class="nav-label">知识范围</div>
        <div class="scope active">
          <span class="scope-dot" />
          制度库 · policies
        </div>
        <div class="scope muted">
          <span class="scope-dot dim" />
          订单事实 · Tool
        </div>
      </div>

      <div class="nav-block">
        <div class="nav-label">快捷问题</div>
        <button
          v-for="q in quickQuestions"
          :key="q"
          type="button"
          class="nav-q"
          @click="panelRef?.send?.(q)"
        >
          {{ q }}
        </button>
      </div>

      <div class="sidebar-foot">
        <div class="env-pill">本地演示</div>
        <p class="foot-hint">制度走 SSE；查单走图编排 + RBAC。历史依赖 Redis（已 compose 起）。</p>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="topbar-left">
          <h1>对话工作台</h1>
          <p>检索制度摘录 · 权限控制下的订单查询</p>
        </div>
        <div class="topbar-right">
          <template v-if="user">
            <div class="user-chip">
              <span class="user-role">{{ user.role || 'user' }}</span>
              <span class="user-name">{{ user.username }}</span>
            </div>
            <button type="button" class="btn-ghost" @click="onLogout">退出</button>
          </template>
          <template v-else>
            <span class="guest-hint">访客 · 仅制度问答</span>
            <button type="button" class="btn-accent" @click="showLogin = true">
              登录
            </button>
          </template>
        </div>
      </header>

      <main class="main">
        <ChatPanel ref="panelRef" @session-updated="refreshSessions" />
      </main>
    </div>

    <div v-if="showLogin" class="modal-mask" @click.self="showLogin = false">
      <div class="modal" role="dialog" aria-labelledby="login-title">
        <h2 id="login-title">登录演示账号</h2>
        <p class="modal-desc">
          JWT 写入本地后，查单请求自动带 Bearer。演示：tutor / tutor123
        </p>
        <label>
          用户名
          <input v-model="loginForm.username" autocomplete="username" />
        </label>
        <label>
          密码
          <input
            v-model="loginForm.password"
            type="password"
            autocomplete="current-password"
            @keydown.enter="doLogin"
          />
        </label>
        <p v-if="loginError" class="login-error">{{ loginError }}</p>
        <div class="modal-actions">
          <button type="button" class="btn-ghost" @click="showLogin = false">
            取消
          </button>
          <button type="button" class="btn-accent" :disabled="loginLoading" @click="doLogin">
            {{ loginLoading ? '登录中…' : '登录' }}
          </button>
        </div>
        <div class="demo-accounts">
          <button type="button" class="chip" @click="fill('tutor', 'tutor123')">
            tutor 可查单
          </button>
          <button type="button" class="chip" @click="fill('lecturer', 'lec123')">
            lecturer 不可查单
          </button>
          <button type="button" class="chip" @click="fill('admin', 'admin123')">
            admin
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import ChatPanel from './components/ChatPanel.vue'
import { getChatHistory, postLogin } from './api/client'
import { clearAuth, getUser, setAuth } from './composables/useAuth'
import { useSession } from './composables/useSession'
import { readCachedMessages } from './composables/sessionMessageCache'

const {
  getSessionId,
  setSessionId,
  listSessions,
  resetSession,
} = useSession()

const panelRef = ref(null)
const showLogin = ref(false)
const loginLoading = ref(false)
const loginError = ref('')
const user = ref(getUser())
const loginForm = ref({ username: 'tutor', password: 'tutor123' })
const sessions = ref([])
const currentSessionId = ref(getSessionId())

const quickQuestions = [
  '现在有多少订单？',
  '多少老师呢？',
  '数学班有几个？',
  '订单来源分布怎么样？',
  '学员05的订单',
  '待审核工单有多少？',
]

function refreshSessions() {
  sessions.value = listSessions()
  currentSessionId.value = getSessionId()
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi}`
}

async function openSession(id) {
  if (!id) return
  setSessionId(id)
  currentSessionId.value = id
  try {
    const data = await getChatHistory(id)
    let msgs = data.messages || []
    if (!msgs.length) {
      msgs = readCachedMessages(id)
    }
    panelRef.value?.setMessages?.(msgs)
    if (!msgs.length) {
      console.warn('该会话在 Redis/本地均无消息（可能 Redis 未开时聊的已丢）')
    }
  } catch (e) {
    const local = readCachedMessages(id)
    panelRef.value?.setMessages?.(local)
    console.warn('load history failed, fallback local', e)
  }
  refreshSessions()
}

function fill(u, p) {
  loginForm.value = { username: u, password: p }
}

/** 换账号后：切到该用户自己的会话列表与当前消息（勿沿用上一人内存里的气泡） */
async function switchAccountUi() {
  refreshSessions()
  await openSession(getSessionId())
}

async function doLogin() {
  loginError.value = ''
  loginLoading.value = true
  try {
    const data = await postLogin(loginForm.value.username, loginForm.value.password)
    setAuth(data.access_token, data.user)
    user.value = data.user
    showLogin.value = false
    await switchAccountUi()
  } catch (e) {
    loginError.value = e.message || '登录失败'
  } finally {
    loginLoading.value = false
  }
}

async function onLogout() {
  clearAuth()
  user.value = null
  await switchAccountUi()
}

function onNewChat() {
  resetSession()
  panelRef.value?.clearMessages?.()
  refreshSessions()
}

onMounted(async () => {
  refreshSessions()
  // 刷新后自动恢复当前会话气泡，避免空白只能去点历史
  await openSession(getSessionId())
})
</script>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background: var(--bg-sidebar);
  color: #e7ecf1;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
  overflow-y: auto;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 4px 8px;
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(145deg, #14b8a6, #0f766e 55%, #134e4a);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.brand-name {
  font-weight: 600;
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}

.brand-sub {
  font-size: 0.7rem;
  color: #8b98a5;
  margin-top: 2px;
  font-family: var(--font-mono);
}

.btn-new {
  width: 100%;
  border: 1px solid #2a3441;
  background: var(--bg-sidebar-hover);
  color: #f1f5f9;
  border-radius: 8px;
  padding: 10px 12px;
  text-align: left;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.btn-new:hover {
  background: #243040;
  border-color: #3d4f63;
}

.nav-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7c8f;
  padding: 0 8px;
  margin-bottom: 4px;
}

.scope {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 0.82rem;
}

.scope.active {
  background: rgba(20, 184, 166, 0.12);
  color: #99f6e4;
}

.scope.muted {
  color: #7a8a9a;
}

.scope-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #2dd4bf;
}

.scope-dot.dim {
  background: #4b5563;
}

.nav-q {
  border: none;
  background: transparent;
  color: #b8c4d0;
  text-align: left;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 0.8rem;
  line-height: 1.35;
}

.nav-q:hover {
  background: var(--bg-sidebar-hover);
  color: #fff;
}

.nav-q.active {
  background: rgba(20, 184, 166, 0.14);
  color: #99f6e4;
}

.history-block {
  max-height: 220px;
  overflow-y: auto;
}

.hist-empty {
  margin: 0;
  padding: 4px 10px;
  font-size: 0.72rem;
  color: #64748b;
}

.hist-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  border: none;
  background: transparent;
  color: #b8c4d0;
  text-align: left;
  padding: 8px 10px;
  border-radius: 8px;
}

.hist-item:hover {
  background: var(--bg-sidebar-hover);
  color: #fff;
}

.hist-item.active {
  background: rgba(20, 184, 166, 0.14);
  color: #99f6e4;
}

.hist-title {
  font-size: 0.8rem;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.hist-time {
  font-size: 0.65rem;
  font-family: var(--font-mono);
  color: #64748b;
}

.sidebar-foot {
  margin-top: auto;
  padding: 8px;
}

.env-pill {
  display: inline-block;
  font-size: 0.68rem;
  font-family: var(--font-mono);
  padding: 3px 8px;
  border-radius: 999px;
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #334155;
}

.foot-hint {
  margin: 8px 0 0;
  font-size: 0.72rem;
  color: #64748b;
  line-height: 1.4;
}

.workspace {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--bg-main);
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 28px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-soft);
}

.topbar-left h1 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}

.topbar-left p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--accent-soft);
  border: 1px solid #99f6e4;
}

.user-role {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 600;
}

.user-name {
  font-size: 0.85rem;
  color: var(--text);
}

.guest-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.btn-accent,
.btn-ghost {
  border-radius: 8px;
  padding: 8px 14px;
  border: 1px solid transparent;
  font-size: 0.85rem;
}

.btn-accent {
  background: var(--accent);
  color: #fff;
}

.btn-accent:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-accent:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  border-color: var(--border);
  color: var(--text-muted);
}

.btn-ghost:hover {
  border-color: #94a3b8;
  color: var(--text);
}

.main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 20px 28px 28px;
  display: flex;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  z-index: 50;
  padding: 20px;
}

.modal {
  width: min(400px, 100%);
  background: var(--bg-panel);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border-soft);
}

.modal h2 {
  margin: 0;
  font-size: 1.1rem;
}

.modal-desc {
  margin: 8px 0 18px;
  font-size: 0.82rem;
  color: var(--text-muted);
  line-height: 1.45;
}

.modal label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.modal input {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  color: var(--text);
}

.modal input:focus {
  outline: 2px solid rgba(15, 118, 110, 0.25);
  border-color: var(--accent);
}

.login-error {
  color: var(--danger);
  font-size: 0.8rem;
  margin: 0 0 10px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.demo-accounts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border-soft);
}

.chip {
  border: 1px solid var(--border);
  background: #f8fafc;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.chip:hover {
  border-color: var(--accent);
  color: var(--accent);
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }
}
</style>
