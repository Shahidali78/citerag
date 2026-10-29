'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Link from 'next/link';
import { ArrowRight, BookOpen, Check, ChevronDown, FileText, LoaderCircle, MessageSquareText, Plus, Search, ShieldCheck, Sparkles, Trash2, UploadCloud, X } from 'lucide-react';

const API = '/api';
type Doc = { id: string; filename: string; chunks: number; created_at: string };
type Citation = { chunk_id: string; marker: string; document_id: string; filename: string; page: number; snippet: string; similarity: number };
type Diagnostic = { chunk_id: string; filename: string; page: number; vector_similarity: number | null; keyword_score: number; fusion_rank: number | null; rerank_score: number | null; selected: boolean };
type Message = { role: 'user' | 'assistant'; content: string; citations?: Citation[]; retrieved_count?: number; diagnostics?: Diagnostic[]; telemetry?: {request_id: string}; };

export default function Home() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [activeSource, setActiveSource] = useState<Citation | null>(null);
  const [topK, setTopK] = useState(5);
  const [retrievalMode, setRetrievalMode] = useState('dense');
  const [candidateCount, setCandidateCount] = useState(20);
  const [threshold, setThreshold] = useState(0.25);
  useEffect(() => { fetch(`${API}/retrieval/config`).then(r => r.json()).then(d => { setRetrievalMode(d.default.mode); setCandidateCount(d.default.candidates); setTopK(d.default.top_k); setThreshold(d.default.threshold); }).catch(() => {}); }, []);
  const [dragging, setDragging] = useState(false);
  const [mode, setMode] = useState('Connecting');
  const [uploadStatus, setUploadStatus] = useState('');
  const [copied, setCopied] = useState<number | null>(null);
  const [showcase, setShowcase] = useState(false);
  const [readOnly, setReadOnly] = useState(true);
  const [samples, setSamples] = useState<string[]>([]);
  useEffect(() => {
    fetch('/api/session').then(r => r.json()).then(s => {setShowcase(s.access_mode === 'showcase'); setReadOnly(s.access_mode === 'showcase' || !s.authenticated);}).catch(() => {});
    fetch('/api/showcase/questions').then(r => r.ok ? r.json() : []).then(setSamples).catch(() => {});
  }, []);
  const panelClose = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (!activeSource) return; const previous = document.activeElement as HTMLElement; panelClose.current?.focus(); const close = (e: KeyboardEvent) => { if (e.key === 'Escape') setActiveSource(null); }; document.addEventListener('keydown', close); return () => { document.removeEventListener('keydown', close); previous?.focus(); }; }, [activeSource]);
  useEffect(() => { fetch(`${API}/health`).then(r => r.json()).then(d => setMode(d.mode === 'showcase' ? 'Saved showcase' : d.mode === 'demo' ? 'Offline demo' : d.openai_configured ? 'OpenAI configured' : 'API key required')).catch(() => setMode('Backend offline')); }, []);
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const refresh = useCallback(async () => {
    try { const r = await fetch(`${API}/documents`); if (!r.ok) throw new Error(r.status === 401 ? 'Sign in above to access your private documents.' : r.status === 503 ? 'Owner live access is not configured on the backend.' : 'Cannot reach the backend. Start FastAPI on port 8000.'); setDocs(await r.json()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Backend unavailable'); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  async function upload(files: FileList | File[]) {
    if (readOnly) {setError('Uploads require owner live access.'); return;}
    if (uploading || busy) return;
    setUploading(true); setError('');
    try {
      let completed = 0;
      for (const file of Array.from(files)) {
        if (!/\.(pdf|txt|md)$/i.test(file.name)) throw new Error('Only PDF, TXT, and Markdown are supported.');
        if (file.size > 20 * 1024 * 1024) throw new Error(`${file.name} exceeds 20 MB.`);
        setUploadStatus(`Indexing ${completed + 1} of ${files.length}: ${file.name}`);
        const form = new FormData(); form.append('file', file);
        const r = await fetch(`${API}/documents`, { method: 'POST', body: form });
        if (!r.ok) { const e = await r.json(); throw new Error(e.detail || `Upload failed: ${file.name}`); }
        completed++; setUploadStatus(`${completed} of ${files.length} indexed`); await refresh();
      }
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed'); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  }

  async function remove(id: string) {
    setError('');
    try { const r = await fetch(`${API}/documents/${id}`, { method: 'DELETE' }); if (!r.ok) throw new Error('Delete failed'); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Delete failed'); }
  }

  async function ask(value = question) {
    const q = value.trim(); if (!q || busy || uploading) return;
    setMessages(old => [...old, { role: 'user', content: q }]); setQuestion(''); setBusy(true); setError(''); setActiveSource(null);
    try {
      const r = await fetch(`${API}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q, top_k: topK, retrieval_mode: retrievalMode, candidate_count: candidateCount, relevance_threshold: threshold }) });
      const data = await r.json(); if (!r.ok) throw new Error(data.detail || 'Question failed');
      setMessages(old => [...old, { role: 'assistant', content: data.answer, citations: data.citations, retrieved_count: data.retrieved_count, diagnostics: data.diagnostics, telemetry: data.telemetry }]);
    } catch (e) { setError(e instanceof Error ? e.message : 'Request failed'); setMessages(old => [...old, { role: 'assistant', content: 'Sorry, I could not complete that request.' }]); }
    finally { setBusy(false); }
  }

  function responseParts(message: Message) {
    const content = message.content.replace(/\[(\d+)\]/g, (marker, n) => message.citations?.some(c => c.marker === marker) ? `[${marker}](#source-${n})` : marker);
    return <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={{
      a: ({href, children}) => {
        const source = message.citations?.find(c => `#source-${c.marker.slice(1,-1)}` === href);
        return source ? <button className="citation-pill" onClick={() => setActiveSource(source)} aria-label={`View ${source.filename}, page ${source.page}`}>{source.marker}</button> : <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
      }
    }}>{content}</ReactMarkdown>;
  }

  async function copyAnswer(content: string, index: number) {
    try { await navigator.clipboard.writeText(content); setCopied(index); } catch { setError('Copy failed. Select the answer text to copy it manually.'); }
  }

  return <div className="shell">
    <aside className="sidebar" inert={!!activeSource}>
      <div className="brand"><span className="brand-icon"><BookOpen size={22}/></span><div><strong>CiteRAG</strong><small>RESEARCH WORKSPACE</small></div></div>
      <button className="new-chat" disabled={busy} onClick={() => { setMessages([]); setActiveSource(null); }}><Plus size={17}/> New conversation <span>Clear</span></button>
      <Link className="eval-link" href="/evaluations">View evaluations</Link><Link className="eval-link" href="/monitoring">Monitoring</Link><div className="side-section"><div className="section-heading"><span>KNOWLEDGE BASE</span><span className="count">{docs.length}</span></div>
        <div aria-disabled={readOnly} className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); void upload(e.dataTransfer.files); }} onClick={() => fileRef.current?.click()} role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click(); }}>
          {uploading ? <LoaderCircle className="spin" size={24}/> : <UploadCloud size={24}/>}<b>{uploading ? 'Processing documents…' : readOnly ? 'Sample knowledge base' : 'Add your sources'}</b><span>{readOnly ? "Uploads require owner live access" : "Drop files or click to browse"}</span><em>PDF, TXT, MD · Max 20 MB</em>
          <input disabled={readOnly} hidden ref={fileRef} type="file" multiple accept=".pdf,.txt,.md" onChange={e => { if (e.target.files) void upload(e.target.files); }}/>
        </div>
        <p className="upload-status" role="status">{uploadStatus}</p><div className="doc-list">{docs.map(doc => <div className="doc" key={doc.id}><span className="doc-icon"><FileText size={17}/></span><div className="doc-name"><strong title={doc.filename}>{doc.filename}</strong><small>{doc.chunks} chunks indexed</small></div><button className="icon-button delete" title="Delete document" aria-label={`Delete ${doc.filename}`} disabled={busy || uploading || readOnly} onClick={() => void remove(doc.id)}><Trash2 size={15}/></button></div>)}{docs.length === 0 && <p className="empty-docs">Your uploaded documents will appear here.</p>}</div>
      </div>
      <div className="sidebar-bottom"><div className="status"><span className="status-dot"/> Evidence-first generation</div><div className="side-foot"><ShieldCheck size={15}/> Grounded answers · Verifiable sources</div></div>
    </aside>
    <main className="main" inert={!!activeSource}>
      <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Research assistant</strong></div><div className="top-actions"><span className="model-badge"><span className="model-dot"/> {mode}</span><div className="avatar">CR</div></div></header>
      <div className="content-area"><div className="conversation">
        {messages.length === 0 ? <div className="welcome"><div className="hero-symbol"><Sparkles size={29}/></div><div className="eyebrow"><span/> INTELLIGENT DOCUMENT RESEARCH</div><h1>Answers you can <em>trust.</em></h1><p>Ask questions across your documents. Get clear answers backed by the exact sources they came from.</p><div className="feature-pills"><span><Search size={15}/> Semantic search</span><span><BookOpen size={15}/> Source citations</span><span><ShieldCheck size={15}/> Evidence-grounded</span></div><div className="suggestions"><div className="suggest-label">TRY ASKING</div>{(showcase ? samples.slice(0,3) : ['Summarize the key points in my documents','What are the most important findings?','Compare the information across sources']).map(s => <button key={s} onClick={() => void ask(s)}><MessageSquareText size={17}/><span>{s}</span><ArrowRight size={16}/></button>)}</div></div> : <div className="thread">{messages.map((m, i) => <div className={`message ${m.role}`} key={i}><div className="message-avatar">{m.role === 'assistant' ? <Sparkles size={17}/> : 'Y'}</div><div className="message-body"><div className="message-label">{m.role === 'assistant' ? 'CiteRAG' : 'You'}</div><div className="message-text">{m.role === 'assistant' ? responseParts(m) : m.content}</div>{m.role === 'assistant' && <button className="copy-button" onClick={() => void copyAnswer(m.content, i)}>{copied === i ? 'Copied' : 'Copy answer'}</button>}{m.diagnostics && m.diagnostics.length > 0 && <details className="retrieval-diagnostics"><summary>Retrieval diagnostics ({m.diagnostics.filter(d => d.selected).length} selected)</summary><p>Scores rank evidence; they are not factual probabilities.</p><div className="eval-table"><table><thead><tr><th>Source</th><th>Cosine</th><th>BM25</th><th>Fusion rank</th><th>Reranker</th><th>Selected</th></tr></thead><tbody>{m.diagnostics.map(d => <tr key={d.chunk_id}><td>{d.filename} p.{d.page}<small className="chunk-id">{d.chunk_id}</small></td><td>{d.vector_similarity?.toFixed(3) ?? 'N/A'}</td><td>{d.keyword_score.toFixed(3)}</td><td>{d.fusion_rank ?? 'N/A'}</td><td>{d.rerank_score?.toFixed(3) ?? 'N/A'}</td><td>{d.selected ? 'Yes' : 'No'}</td></tr>)}</tbody></table></div><small>Request {m.telemetry?.request_id}</small></details>}{m.citations && m.citations.length > 0 && <div className="source-list"><div className="source-title"><BookOpen size={14}/> SOURCES · {m.citations.length} CITED</div>{m.citations.map(c => <button key={c.marker} onClick={() => setActiveSource(c)}><span className="source-marker">{c.marker}</span><span>{c.filename} <small>· p. {c.page}</small></span><ArrowRight size={14}/></button>)}</div>}</div></div>)}{busy && <div className="thinking"><LoaderCircle className="spin" size={17}/> Searching your knowledge base and composing an answer…</div>}<div ref={endRef}/></div>}
      </div></div><div className="composer-wrap">{samples.length > 0 && messages.length === 0 && <div className="sample-questions"><p>{showcase ? "Try a saved example; no API charge" : "Questions from the sample corpus"}</p>{samples.slice(0, 4).map(q => <button key={q} disabled={busy} onClick={() => void ask(q)}>{q}</button>)}</div>}{error && <div className="error" role="alert"><span>{error}</span><button onClick={() => setError('')}><X size={15}/></button></div>}<form className="composer" onSubmit={e => { e.preventDefault(); void ask(); }}><textarea maxLength={4000} aria-label="Ask your documents" placeholder="Ask anything about your documents…" rows={2} value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void ask(); } }}/><details className="retrieval-settings"><summary>Search settings</summary><div className="settings-grid"><label>Retrieval method<select disabled={showcase} aria-label="Retrieval method" value={retrievalMode} onChange={e => setRetrievalMode(e.target.value)}><option value="dense">Dense (recommended)</option><option value="hybrid">Hybrid (recommended): vectors + BM25</option><option value="hybrid_rerank">Hybrid + reranking (experimental)</option></select></label><label>Candidate pool<input disabled={showcase} aria-label="Candidate pool" type="number" min={1} max={100} value={candidateCount} onChange={e => setCandidateCount(Math.max(1,Math.min(100,Number(e.target.value))))}/></label><label>Reranker threshold<input disabled={showcase} aria-label="Relevance threshold" type="number" min={0} max={1} step={0.05} value={threshold} onChange={e => setThreshold(Math.max(0,Math.min(1,Number(e.target.value))))}/></label></div></details><div className="composer-bottom"><label className="retrieval"><Search size={14}/> Retrieve <select disabled={showcase} aria-label="Retrieved chunks" value={topK} onChange={e => setTopK(Number(e.target.value))}>{[3,5,8,12].map(n => <option key={n} value={n}>{n} chunks</option>)}</select><ChevronDown size={12}/></label><button className="send" type="submit" disabled={!question.trim() || busy || uploading} aria-label="Send question">{busy ? <LoaderCircle className="spin" size={19}/> : <ArrowRight size={20}/>}</button></div></form><div className="disclaimer">CiteRAG grounds answers in your documents. Always verify important claims against the original sources.</div></div>
    </main>
    {activeSource && <div className="overlay" onClick={() => setActiveSource(null)}><aside role="dialog" aria-modal="true" aria-label="Evidence details" className="source-panel" onClick={e => e.stopPropagation()}><div className="panel-head"><div><small>RETRIEVED SOURCE</small><h2>Evidence details</h2></div><button ref={panelClose} aria-label="Close evidence" className="icon-button" onClick={() => setActiveSource(null)}><X size={20}/></button></div><div className="panel-doc"><FileText size={21}/><div><strong>{activeSource.filename}</strong><span>Page {activeSource.page} · cosine similarity {activeSource.similarity.toFixed(3)}</span></div></div><div className="panel-label">RETRIEVED EXCERPT <span>{activeSource.marker}</span></div><code className="chunk-id">{activeSource.chunk_id}</code><blockquote>{activeSource.snippet}</blockquote><div className="panel-note"><ShieldCheck size={18}/> Similarity measures retrieval closeness, not factual correctness. Verify each claim against this passage.</div></aside></div>}
  </div>;
}
