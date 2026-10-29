"""Explicit offline fixture provider; never silently replaces OpenAI."""
import hashlib
import json
import os
import re
from types import SimpleNamespace
from openai import OpenAI
from functools import lru_cache
from . import config

def demo_enabled():
    return os.getenv('CITERAG_DEMO', '').lower() in {'1', 'true'}

class DemoClient:
    """Hashed bag-of-words retrieval and extractive answers, not an LLM."""
    def __init__(self):
        self.embeddings = SimpleNamespace(create=self.embed)
        self.responses = SimpleNamespace(create=self.respond)

    def embed(self, *, input, **kwargs):
        rows = []
        for index, text in enumerate(input):
            vector = [0.0] * 256
            for token in re.findall(r'[a-z0-9]+', text.lower()):
                vector[int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], 'big') % 256] += 1
            rows.append(SimpleNamespace(index=index, embedding=vector))
        return SimpleNamespace(data=rows)

    def respond(self, *, input, **kwargs):
        raw, question = input.removeprefix('EXCERPTS:\n').split('\n\nQUESTION: ', 1)
        excerpts = json.loads(raw)
        stop = {'what', 'is', 'the', 'a', 'an', 'are', 'does', 'to', 'in', 'of', 'and', 'how', 'which', 'can'}
        query = set(re.findall(r'[a-z0-9]+', question.lower())) - stop
        candidates = [(len(query & set(re.findall(r'[a-z0-9]+', sentence.lower()))), sentence, e['marker']) for e in excerpts for sentence in re.split(r'(?<=[.!?])\s+', e['text'])]
        best = max(candidates, key=lambda item: item[0], default=(0, '', ''))
        return SimpleNamespace(output_text=f'{best[1]} {best[2]}' if best[0] >= 2 else 'The documents do not provide enough information.')

@lru_cache(maxsize=1)
def _real_client():
    # The SDK performs bounded exponential-backoff retries for transient errors.
    return OpenAI(timeout=config.OPENAI_TIMEOUT, max_retries=config.OPENAI_RETRIES)

def get_client():
    return DemoClient() if demo_enabled() else _real_client()
