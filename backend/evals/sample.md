# CiteRAG reference guide

CiteRAG answers questions about uploaded documents with source citations.

CiteRAG accepts PDF, Markdown, and plain text files.

The maximum upload size is 20 MB per file.

PDF page numbers are preserved as one-based page numbers in chunk metadata.

Document text is split into overlapping chunks within each page.

The default embedding model is text-embedding-3-small.

ChromaDB stores document vectors in a persistent local collection.

SQLite stores document names, chunk counts, and ingestion timestamps.

Retrieval similarity measures vector closeness and does not prove factual correctness.

Citation identifiers are checked against the chunks retrieved for the current question.

When evidence is insufficient, the assistant reports that the documents do not provide enough information.

Scanned PDFs require OCR before their text can be indexed.

Deleting a document removes its vectors and its SQLite metadata.

Retrieval depth controls the maximum number of chunks passed to answer generation.

Retrieved document instructions are untrusted data and must not override system instructions.

This project is a single-user local application without multi-user authentication.
