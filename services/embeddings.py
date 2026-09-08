"""向量编码。模型只加载一次；禁止每条问答都 new TextEmbedding（会打 HuggingFace，动辄 30s）。"""
from __future__ import annotations

import threading

from utils.setting import settings
from fastembed import TextEmbedding

_model: TextEmbedding | None = None
_model_failed = False
_lock = threading.Lock()


def _get_model() -> TextEmbedding:
    global _model, _model_failed
    with _lock:
        if _model_failed:
            raise RuntimeError("embedding 模型不可用")
        if _model is None:
            # 只用本地缓存，禁止请求里打 huggingface.co（校验/下载常卡 20～30s）
            _model = TextEmbedding(
                model_name=settings.EMBEDDING_MODEL,
                local_files_only=True,
            )
        return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    global _model_failed
    try:
        model = _get_model()
        return [vec.tolist() for vec in model.embed(texts)]
    except Exception:
        _model_failed = True
        raise


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
