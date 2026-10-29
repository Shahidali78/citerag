# LinkedIn announcement draft — not posted

I built CiteRAG, a document Q&A workspace with source excerpts you can inspect: document names, PDF pages and persistent chunk IDs.

The stack is Next.js, FastAPI, OpenAI, ChromaDB and SQLite. Retrieval combines semantic search with BM25, with an optional local reranker.

The evaluation taught me more than the first headline. Reranking looked strong on the 16 questions used for calibration. On 40 new questions over the same small corpus, precision increased from 38.75% to 85.42%, but source recall fell from 100% to 84.38% and answer quality dropped. Dense and hybrid remain the recommended choices; aggressive filtering is experimental.

I also separated public exploration from paid inference. The showcase replays clearly labeled saved examples and genuine evaluation reports. Live document access and model calls require owner authentication and usage allowances enforced on the server.

Source, methodology and limitations: https://github.com/Shahidali78/citerag

This is a portfolio project, not a claim of production-scale or universally reliable RAG. A protected deployment is being prepared; no public application URL is announced here.

#AIEngineering #RAG #FastAPI #Nextjs #OpenAI
