from typing import List
from django.conf import settings

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

_model = None

def _get_model():
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise ImportError("sentence-transformers library is not installed. Install with: pip install sentence-transformers")
    
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.AI_EMBED_MODEL_NAME, device="cpu")
    return _model

def embed_texts(texts: List[str]) -> List[List[float]]:
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise ImportError("sentence-transformers library is not installed. Install with: pip install sentence-transformers")
    
    m = _get_model()
    bs = max(1, min(settings.AI_EMBED_BATCH_SIZE, len(texts)))
    embeddings = m.encode(texts, normalize_embeddings=True, convert_to_numpy=False, batch_size=bs)
    # embeddings is already a list when convert_to_numpy=False
    return embeddings


def chunk_text(s: str, max_chars=1200, max_chunks=40):
    out, cur, n = [], [], 0
    for line in s.splitlines():
        if n + len(line) + 1 > max_chars:
            out.append("\n".join(cur)); cur, n = [], 0
            if len(out) >= max_chunks: break
        cur.append(line); n += len(line) + 1
    if cur and len(out) < max_chunks:
        out.append("\n".join(cur))
    return out