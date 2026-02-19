from typing import List
from django.conf import settings
import requests


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using Ollama API"""
    ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
    model_name = getattr(settings, 'OLLAMA_EMBED_MODEL', 'nomic-embed-text')

    embeddings = []
    for text in texts:
        response = requests.post(
            f'{ollama_url}/api/embeddings',
            json={
                'model': model_name,
                'prompt': text
            }
        )
        response.raise_for_status()
        embeddings.append(response.json()['embedding'])

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