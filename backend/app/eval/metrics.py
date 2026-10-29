import re

def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def lexical_f1(prediction: str, reference: str) -> float:
    a, b = tokens(re.sub(r'\[\d+\]', '', prediction)), tokens(reference)
    if not a or not b:
        return float(a == b)
    overlap = len(a & b)
    return round(2 * overlap / (len(a) + len(b)), 4)

def source_recall(retrieved: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    return round(len(set(retrieved) & set(expected)) / len(set(expected)), 4)

def citation_validity(answer: str, markers: list[str]) -> float:
    cited = re.findall(r"\[\d+\]", answer)
    if not cited:
        return 0.0
    return round(sum(f'[{int(m[1:-1])}]' in markers for m in cited) / len(cited), 4)

def source_precision(retrieved: list[str], expected: list[str]) -> float:
    return round(sum(source in expected for source in retrieved) / len(retrieved), 4) if retrieved else 0.0

def reciprocal_rank(retrieved: list[str], expected: list[str]) -> float:
    return next((round(1 / rank, 4) for rank, source in enumerate(retrieved, 1) if source in expected), 0.0)

def evidence_coverage(answer: str, excerpts: list[str]) -> float:
    """Lexical proxy only; token overlap does not establish entailment."""
    words = tokens(re.sub(r'\[\d+\]', '', answer))
    return round(len(words & tokens(' '.join(excerpts))) / len(words), 4) if words else 0.0

def support_accuracy(citations: list, expected_evidence: str) -> float | None:
    if not expected_evidence:
        return None
    expected = tokens(expected_evidence)
    return round(sum(len(tokens(c.snippet) & expected) / max(1, len(expected)) for c in citations) / len(citations), 4) if citations else 0.0

