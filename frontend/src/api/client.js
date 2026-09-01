import { authHeaders } from '../composables/useAuth'

const CHAT_TIMEOUT_MS = 45_000
const STREAM_TIMEOUT_MS = 60_000

async function request(path, options = {}, timeoutMs = CHAT_TIMEOUT_MS) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
        ...(options.headers || {}),
      },
    })
    if (!res.ok) {
      const text = await res.text()
      let detail = text
      try {
        const j = JSON.parse(text)
        detail = j.detail || j.message || text
      } catch {
        /* 非 JSON 正文原样抛出 */
      }
      throw new Error(
        typeof detail === 'string' ? detail.slice(0, 300) : `HTTP ${res.status}`
      )
    }
    try {
      return await res.json()
    } catch {
      throw new Error('服务器返回了无法解析的内容')
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(`请求超时（${Math.round(timeoutMs / 1000)} 秒），请重试或换完整问法`)
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

/** POST /api/auth/login */
export function postLogin(username, password) {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

/** GET /api/chat/history?session_id= */
export function getChatHistory(sessionId) {
  const qs = new URLSearchParams({ session_id: sessionId })
  return request(`/api/chat/history?${qs}`)
}

/** POST /api/chat（非流式：LangGraph + tool loop） */
export async function postChat(question, sessionId) {
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      question,
      session_id: sessionId,
    }),
  })
}

/**
 * POST /api/chat/stream — SSE；onToken 每段回调。
 * 返回完整答案字符串。
 */
export async function postChatStream(question, sessionId, onToken) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS)
  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify({
        question,
        session_id: sessionId,
      }),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || `HTTP ${res.status}`)
    }
    if (!res.body) {
      throw new Error('浏览器不支持流式响应')
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let answer = ''

    let sawDone = false
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() || ''

      for (const block of blocks) {
        const dataLines = block
          .split('\n')
          .filter((row) => row.startsWith('data: '))
          .map((row) => row.slice(6))
        if (!dataLines.length) continue
        const data = dataLines.join('\n')
        if (data === '[DONE]') {
          sawDone = true
          return answer
        }
        let piece = data
        try {
          // 后端用 json.dumps 包一层，保留换行
          const parsed = JSON.parse(data)
          if (typeof parsed === 'string') piece = parsed
        } catch {
          /* 兼容旧协议纯文本 */
        }
        if (piece.startsWith('[ERROR]')) {
          throw new Error(piece.slice('[ERROR]'.length).trim() || '流式处理失败')
        }
        answer += piece
        if (onToken) onToken(piece)
      }
    }
    if (!sawDone) {
      throw new Error(answer ? '连接中断，回复可能不完整' : '连接中断，未收到回复')
    }
    return answer
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(`流式请求超时（${Math.round(STREAM_TIMEOUT_MS / 1000)} 秒），请重试`)
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}
