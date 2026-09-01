import { stripMarkdownInline } from './formatAnswer'

/**
 * 把助手回复拆成「正文 / 表格」交替块，保留多段 Markdown 表（原先只抽第一张会掏空「一、二、」）。
 * @returns {{ blocks: Array<{ type: 'text', text: string } | { type: 'table', headers: string[], rows: string[][] }> }}
 */
export function parseAnswerBlocks(raw) {
  const text = stripMarkdownInline((raw || '').trim())
  if (!text) return { blocks: [] }

  const mdBlocks = splitMarkdownTables(text)
  if (mdBlocks.some((b) => b.type === 'table')) {
    return { blocks: mdBlocks.filter((b) => b.type !== 'text' || b.text) }
  }

  const json = tryJsonArray(text)
  if (json) return { blocks: [{ type: 'table', ...json }] }

  const kv = tryKeyValueList(text)
  if (kv) return { blocks: [{ type: 'table', ...kv }] }

  return { blocks: [{ type: 'text', text }] }
}

/**
 * 兼容旧调用：首张表 + 剩余纯文本（会丢掉其它表，新 UI 请用 parseAnswerBlocks）。
 */
export function parseAnswerTable(raw) {
  const { blocks } = parseAnswerBlocks(raw)
  const table = blocks.find((b) => b.type === 'table') || null
  const text = blocks
    .filter((b) => b.type === 'text')
    .map((b) => b.text)
    .join('\n\n')
    .trim()
  return {
    table: table
      ? { headers: table.headers, rows: table.rows }
      : null,
    text,
  }
}

function isTableLine(line) {
  const t = line.trim()
  return t.startsWith('|') && t.endsWith('|')
}

function parseTableLines(tableLines) {
  if (tableLines.length < 2) return null
  const parseRow = (line) =>
    line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((c) => c.trim())

  const headers = parseRow(tableLines[0])
  let dataStart = 1
  if (/^[\s|:-]+$/.test(tableLines[1].replace(/\|/g, ''))) {
    dataStart = 2
  }
  const rows = tableLines.slice(dataStart).map(parseRow)
  if (!rows.length) return null
  return { headers, rows }
}

/** 按出现顺序切成 text / table 块 */
function splitMarkdownTables(text) {
  const lines = text.split(/\r?\n/)
  const blocks = []
  let i = 0
  let textBuf = []

  const flushText = () => {
    const t = textBuf.join('\n').trim()
    textBuf = []
    if (t) blocks.push({ type: 'text', text: t })
  }

  while (i < lines.length) {
    if (isTableLine(lines[i])) {
      const tableLines = []
      while (i < lines.length && isTableLine(lines[i])) {
        tableLines.push(lines[i])
        i++
      }
      const parsed = parseTableLines(tableLines)
      if (parsed) {
        flushText()
        blocks.push({ type: 'table', headers: parsed.headers, rows: parsed.rows })
      } else {
        textBuf.push(...tableLines)
      }
      continue
    }
    textBuf.push(lines[i])
    i++
  }
  flushText()
  return blocks
}

function tryJsonArray(text) {
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/i)
  const candidate = fence ? fence[1].trim() : text.trim()
  if (!candidate.startsWith('[')) return null
  try {
    const data = JSON.parse(candidate)
    if (!Array.isArray(data) || !data.length) return null
    if (data.every((x) => x !== null && typeof x === 'object' && !Array.isArray(x))) {
      const headers = [...new Set(data.flatMap((row) => Object.keys(row)))]
      const rows = data.map((row) => headers.map((h) => stringifyCell(row[h])))
      return { headers, rows }
    }
    if (data.every((x) => typeof x !== 'object' || x === null)) {
      return {
        headers: ['项'],
        rows: data.map((x) => [stringifyCell(x)]),
      }
    }
  } catch {
    /* ignore */
  }
  return null
}

/** 至少 2 行「- 键：值」或「1. 键：值」→ 两列表格 */
function tryKeyValueList(text) {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  const pairs = []
  for (const line of lines) {
    const m = line.match(/^(?:[-*•]|\d+[.)])\s*(.+?)[:：]\s*(.+)$/)
    if (!m) {
      if (pairs.length >= 2) break
      return null
    }
    pairs.push([m[1].trim(), m[2].trim()])
  }
  if (pairs.length < 2) return null
  return { headers: ['项', '内容'], rows: pairs }
}

function stringifyCell(v) {
  if (v === null || v === undefined) return ''
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
