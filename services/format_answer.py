"""助手正文展示清洗：去掉 Markdown 噪音与空壳「一、二、」标题。"""
from __future__ import annotations

import re

_OUTLINE_HEADER = re.compile(r"^[一二三四五六七八九十百千]+、.+")
_CN_NUM = list("一二三四五六七八九十")
_HR = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$", re.M)
_BOLD = re.compile(r"\*\*([^*]*)\*\*")
_ITALIC = re.compile(r"\*([^*\n]+)\*")
_HEADING = re.compile(r"^#{1,6}\s+", re.M)
_MULTI_NL = re.compile(r"\n{3,}")
_NOISE_ONLY = re.compile(r"^[-–—*•·.。、：:;；\s]+$")


def _is_outline(line: str) -> bool:
    return bool(_OUTLINE_HEADER.match(line.strip()))


def _is_blank_or_noise(line: str) -> bool:
    t = line.strip()
    return (not t) or bool(_NOISE_ONLY.match(t))


def strip_empty_outline_headers(text: str) -> str:
    lines = (text or "").splitlines()
    header_idx = [i for i, ln in enumerate(lines) if _is_outline(ln)]
    drop: set[int] = set()
    for k, start in enumerate(header_idx):
        end = header_idx[k + 1] if k + 1 < len(header_idx) else len(lines)
        body = lines[start + 1 : end]
        has_content = any(
            (not _is_blank_or_noise(ln)) and (not _is_outline(ln)) for ln in body
        )
        if not has_content:
            drop.add(start)

    kept = [ln for i, ln in enumerate(lines) if i not in drop]
    n = 0
    out: list[str] = []
    for ln in kept:
        if _is_outline(ln) and n < len(_CN_NUM):
            ln = re.sub(
                r"^([ \t]*)[一二三四五六七八九十百千]+、",
                rf"\1{_CN_NUM[n]}、",
                ln,
                count=1,
            )
            n += 1
        out.append(ln)
    return _MULTI_NL.sub("\n\n", "\n".join(out)).strip()


def clean_assistant_text(text: str) -> str:
    """落库/返回前清洗助手正文。"""
    if not text:
        return ""
    s = str(text)
    s = _BOLD.sub(r"\1", s)
    s = _ITALIC.sub(r"\1", s)
    s = _HEADING.sub("", s)
    s = s.replace("**", "")
    s = _HR.sub("", s)
    s = _MULTI_NL.sub("\n\n", s)
    s = strip_empty_outline_headers(s)
    return s.strip()
