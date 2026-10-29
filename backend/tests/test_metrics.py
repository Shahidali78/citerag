from app.eval.metrics import citation_validity, lexical_f1, source_recall
from app.rag import valid_markers
from app.rag import validate_answer

def test_mixed_uncertainty_preserves_cited_supported_fact():
    raw='The documents do not provide enough information about isolation. However, the project has no multi-user authentication [1].'
    answer, markers=validate_answer(raw,1)
    assert answer == raw and markers == [1]
    answer, markers=validate_answer('The documents do not provide enough information. [1]',1)
    assert markers == [] and '[1]' not in answer

def test_marker_validation():
    assert valid_markers("Claim [2] [9] and [2]", 3) == [2]

def test_source_recall():
    assert source_recall(["a.pdf"], ["a.pdf", "b.pdf"]) == 0.5

def test_lexical_f1():
    assert lexical_f1("the cat", "cat") == 0.6667

def test_citation_validity():
    assert citation_validity("hello [1] and [8]", ["[1]"]) == 0.5
    assert citation_validity("uncited", []) == 0

