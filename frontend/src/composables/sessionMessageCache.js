import { storageOwner } from './useSession'

function cacheKey() {
  return `edu-crm-langgraph:msg_cache:${storageOwner()}`
}

function readCache() {
  try {
    const raw = localStorage.getItem(cacheKey())
    const obj = raw ? JSON.parse(raw) : {}
    return obj && typeof obj === 'object' ? obj : {}
  } catch {
    return {}
  }
}

function writeCache(obj) {
  const entries = Object.entries(obj).slice(0, 40)
  localStorage.setItem(cacheKey(), JSON.stringify(Object.fromEntries(entries)))
}

/** 把某会话消息备份到本地（Redis 挂了也能点开历史） */
export function cacheSessionMessages(sessionId, messages) {
  if (!sessionId) return
  const all = readCache()
  all[sessionId] = (messages || [])
    .filter((m) => m && (m.role === 'user' || m.role === 'assistant'))
    .map((m) => ({ role: m.role, content: m.content || '' }))
  writeCache(all)
}

export function readCachedMessages(sessionId) {
  if (!sessionId) return []
  return readCache()[sessionId] || []
}
