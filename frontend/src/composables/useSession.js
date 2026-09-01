import { getUser } from './useAuth'

/** 当前账号命名空间：登录用户名，未登录用 guest */
export function storageOwner() {
  const u = getUser()
  const name = (u?.username || '').trim().toLowerCase()
  return name || 'guest'
}

function sessionIdKey() {
  return `edu-crm-langgraph:session_id:${storageOwner()}`
}

function indexKey() {
  return `edu-crm-langgraph:session_index:${storageOwner()}`
}

function readIndex() {
  try {
    const raw = localStorage.getItem(indexKey())
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function writeIndex(list) {
  localStorage.setItem(indexKey(), JSON.stringify(list.slice(0, 50)))
}

export function useSession() {
  function getSessionId() {
    let id = localStorage.getItem(sessionIdKey())
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(sessionIdKey(), id)
      touchSession(id, '新会话')
    }
    return id
  }

  function setSessionId(id) {
    localStorage.setItem(sessionIdKey(), id)
  }

  function listSessions() {
    return readIndex().sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
  }

  /** 更新/插入侧栏索引（标题一般用首问） */
  function touchSession(id, title) {
    if (!id) return
    const list = readIndex().filter((s) => s.id !== id)
    const prev = readIndex().find((s) => s.id === id)
    list.unshift({
      id,
      title: (title || prev?.title || '新会话').slice(0, 40),
      updatedAt: Date.now(),
    })
    writeIndex(list)
  }

  function resetSession() {
    const id = crypto.randomUUID()
    localStorage.setItem(sessionIdKey(), id)
    touchSession(id, '新会话')
    return id
  }

  return {
    getSessionId,
    setSessionId,
    listSessions,
    touchSession,
    resetSession,
  }
}
