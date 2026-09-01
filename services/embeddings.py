"""第 3 步起：你自己实现 embed_texts / embed_query（见练习引导）。"""
from __future__ import annotations
from utils.setting import settings
from fastembed import TextEmbedding
def _get_model():
    return TextEmbedding(model_name=settings.EMBEDDING_MODEL)
def embed_texts(texts:list[str]):
   data =  _get_model()
   list1 =list(data.embed(texts))
   result = []
   for l in list1:
       result.append(l.tolist())
   return result

# TODO 第 3 步：在这里写 embedding 函数
def embed_query(text):
    return embed_texts([text])[0]