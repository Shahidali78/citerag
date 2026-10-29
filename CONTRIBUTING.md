# Contributing

Keep changes scoped and preserve the measured baseline in `docs/baseline`. Add regression tests for retrieval, citations, error handling, or privacy changes. Do not edit historical scores to make a comparison look better.

Run `python -m pytest -q` from backend, then `npm.cmd run typecheck` and `npm.cmd run build` from frontend. Unit tests use isolated stores and a fixture provider; CI never needs an OpenAI key. Browser tests require an explicitly configured test backend. Run them against a separate corpus, not private working documents.

Real evaluations and integration checks incur API usage. Keep them opt-in. Preserve the dataset, corpus manifest, model settings, retrieval parameters, raw outputs, and timing definitions in each comparison. Disclose calibration on evaluation data and distinguish lexical proxies from model judgments.

Never commit `.env`, credentials, private documents, production databases, or private evaluation outputs. Only public synthetic example reports belong under docs. Do not publish a deployment or change data ownership assumptions as an incidental part of a code change.

Open pull requests with the concrete problem, resulting behavior, relevant tests, and remaining limits. The project uses the MIT license.
