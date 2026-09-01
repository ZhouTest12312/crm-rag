/**
 * 展示前去掉 LLM 常见的 Markdown 噪音（不做完整 MD 渲染）。
 * 目标：气泡里是可读正文，而不是 `---` / 空壳标题等原稿痕迹。
 */
export function stripMarkdownInline(text) {
  if (!text) return ''
  let s = String(text)
    // 行内加粗/斜体
    .replace(/\*\*([^*]*)\*\*/g, '$1')
    .replace(/\*([^*\n]+)\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*/g, '')
    // Markdown 分隔线（单独一行的 --- / *** / ___）
    .replace(/^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$/gm, '')
    // 多余空行收成最多一个空行
    .replace(/\n{3,}/g, '\n\n')

  s = stripEmptyOutlineHeaders(s)
  return s.trim()
}

/** 中文大标题：一、二、三…（不含「1. 正文」这种同条列表） */
const OUTLINE_HEADER = /^[一二三四五六七八九十百千]+、.+/
const CN_NUM = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

function isOutlineHeader(line) {
  return OUTLINE_HEADER.test(String(line || '').trim())
}

/** 空行，或只有标点/项目符号、没有实质正文 */
function isBlankOrNoise(line) {
  const t = String(line || '').trim()
  if (!t) return true
  if (/^[-–—*•·.。、：:;；\s]+$/.test(t)) return true
  return false
}

/**
 * 去掉「标题下没有实质正文」的空壳大纲标题，并对剩余标题重新编号。
 * 例如只剩「三、注意事项」→「一、注意事项」。
 */
export function stripEmptyOutlineHeaders(text) {
  const lines = String(text || '').split(/\r?\n/)
  const headerIdx = []
  for (let i = 0; i < lines.length; i++) {
    if (isOutlineHeader(lines[i])) headerIdx.push(i)
  }

  const drop = new Set()
  for (let k = 0; k < headerIdx.length; k++) {
    const start = headerIdx[k]
    const end = k + 1 < headerIdx.length ? headerIdx[k + 1] : lines.length
    const body = lines.slice(start + 1, end)
    const hasContent = body.some((l) => !isBlankOrNoise(l) && !isOutlineHeader(l))
    if (!hasContent) drop.add(start)
  }

  const kept = lines.filter((_, i) => !drop.has(i))
  let n = 0
  const renumbered = kept.map((line) => {
    if (!isOutlineHeader(line) || n >= CN_NUM.length) return line
    return line.replace(
      /^([ \t]*)[一二三四五六七八九十百千]+、/,
      `$1${CN_NUM[n++]}、`
    )
  })
  return renumbered.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}
