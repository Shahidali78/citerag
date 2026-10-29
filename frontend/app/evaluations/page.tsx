"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

type Row = { question: string; answerable?: boolean; strict_abstention?: number | null; evidence_recall_at_k?: number | null; answer?: string; reference_answer?: string; latency_seconds?: number; retrieval_seconds?: number; citation_validity?: number | null; source_recall_at_k?: number | null; answer_correctness_judge?: number | null; faithfulness_judge?: number | null; citation_support_judge?: number | null; selected_chunk_ids?: string[] };
type Report = { dataset_split?: string; evaluation_protocol?: string; metric_denominators?: Record<string,number>; answerable_examples?: number; unanswerable_examples?: number; available?: boolean; message?: string; run_id?: string; label?: string; mode?: string; created_at?: string; updated_at?: string; chat_model?: string; embedding_model?: string; examples?: number; top_k?: number; evaluation_kind?: string; summary?: Record<string, number | null>; results?: Row[]; judge_missing_counts?: Record<string, number>; retrieval_configuration?: {mode: string; threshold: number; candidates: number}; calibration_note?: string; embedding_note?: string };
const API = '/api';
const explanations: Record<string,string> = {
 source_recall_at_k: 'Expected source documents found among selected evidence.', source_precision_at_k: 'Selected chunks belonging to expected source documents; denominator is actual selected count.',
 mrr: 'Reciprocal rank of the first expected source.', answer_lexical_f1: 'Token overlap with the reference, excluding citation numbers. A lexical proxy, not semantic correctness.',
 faithfulness_lexical_proxy: 'Answer token coverage in selected evidence. Does not establish entailment.', citation_support_lexical_proxy: 'Expected evidence token coverage in cited excerpts. Requires human review.',
 citation_validity: 'Raw citation markers linked to real selected chunks, before cleanup.', latency_seconds: 'Mean measured answer pipeline latency. Check run conditions before comparing.',
 answer_correctness_judge: 'Optional OpenAI semantic comparison against reference answers.', faithfulness_judge: 'Optional OpenAI judgment of support by cited evidence.', citation_support_judge: 'Optional OpenAI judgment of numbered citation support.',
 expected_evidence_coverage: 'Expected evidence tokens covered by selected passages; complements filename recall.', retrieval_seconds: 'Measured local retrieval and reranking time.', selected_count: 'Mean selected evidence chunks per question.',
 evidence_recall_at_k:'Gold evidence groups covered by selected chunks; overlapping duplicates count as alternatives, not separate recall requirements.',
 evidence_precision_at_k:'Selected chunks covering a quoted gold fact; stricter than filename relevance.', evidence_mrr:'Reciprocal rank of the first gold-evidence chunk.',
 strict_abstention:'Unanswerable questions answered with an insufficient-evidence response and no citations.', false_abstention:'Answerable questions refused; lower is better.',
 answerable_citation_coverage:'Answerable questions with at least one returned valid citation; prevents marker validity from hiding missing citations.',
 generation_input_tokens:'Provider-reported generation input tokens across this run.',generation_output_tokens:'Provider-reported generation output tokens across this run.',generation_total_tokens:'Total provider-reported generation tokens; excludes embedding and judging.'
};
function formatted(key:string, value:number|null|undefined) { return value == null ? 'N/A' : key.includes('seconds') ? `${value.toFixed(3)}s` : key.includes('tokens') ? value.toLocaleString() : key === 'selected_count' ? value.toFixed(2) : `${(value*100).toFixed(1)}%`; }
export default function Evaluations() {
 const [report,setReport]=useState<Report|null>(null), [baseline,setBaseline]=useState<Report|null>(null), [runs,setRuns]=useState<Report[]>([]);
 const firstLoad = useRef(true);
 const latestRead = useRef(0);
 const [selected,setSelected]=useState('baseline'), [filter,setFilter]=useState('all'), [error,setError]=useState(''), [loading,setLoading]=useState(false);
 async function read(id:string, base=baseline) {
  const request=++latestRead.current;
  setLoading(true);setError('');setSelected(id);
  try { if(id==='baseline') setReport(base); else { const r=await fetch(`${API}/evaluations/runs/${id}`);if(!r.ok)throw new Error('Saved run unavailable');const value:Report=await r.json();if(request===latestRead.current)setReport(value); } }
  catch(e){if(request===latestRead.current)setError(e instanceof Error?e.message:'Request failed');}finally{if(request===latestRead.current)setLoading(false);}
 }
 async function refresh() {
  setLoading(true);setError('');
  try {
   const [baseResponse,historyResponse]=await Promise.all([fetch(`${API}/evaluations`,{cache:'no-store'}),fetch(`${API}/evaluations/runs`,{cache:'no-store'})]);
   if(!baseResponse.ok||!historyResponse.ok)throw new Error('Could not load evaluation history.');
   const base:Report=await baseResponse.json(), history:Report[]=await historyResponse.json();setBaseline(base);setRuns(history);
   const preferred=history.find(r=>r.dataset_split==='held_out'&&r.retrieval_configuration?.mode==='hybrid_rerank')||history.find(r=>r.label?.includes('validated partial answers'))||history.find(r=>r.evaluation_kind==='answers'&&r.retrieval_configuration?.mode==='hybrid_rerank');
   const target=firstLoad.current?(preferred?.run_id||'baseline'):selected;firstLoad.current=false;await read(target,base);
  }catch(e){setError(e instanceof Error?e.message:'Backend unavailable');setLoading(false);}
 }
 useEffect(()=>{void refresh();},[]);
 const visible=runs.filter(r=>filter==='all'||(r.retrieval_configuration?.mode||'dense')===filter);
 const failures=report?.results?.filter(r=>(r.source_recall_at_k??1)<1||(r.evidence_recall_at_k??1)<1||r.strict_abstention===0||(r.citation_validity??1)<1||(r.answer_correctness_judge??1)<.8||(r.faithfulness_judge??1)<.8||(r.citation_support_judge??1)<.8)||[];
 return <main className="evaluations"><nav><Link href="/">Back to research workspace</Link><Link href="/monitoring">Monitoring</Link><button onClick={()=>void refresh()} disabled={loading}>{loading?'Loading...':'Refresh results'}</button></nav>
 <p className="eyebrow">QUALITY & EVIDENCE</p><h1>Evaluation dashboard</h1><p>Immutable runs, explicit retrieval settings, and measured outcomes. Lexical and model-judged scores need human review.</p>
 <div className="settings-grid run-controls"><label>Retrieval configuration<select aria-label="Evaluation retrieval configuration" value={filter} onChange={e=>{setFilter(e.target.value);const next=runs.find(r=>e.target.value==='all'||(r.retrieval_configuration?.mode||'dense')===e.target.value);void read(next?.run_id||'baseline');}}><option value="all">All configurations</option><option value="dense">Dense baseline</option><option value="hybrid">Hybrid</option><option value="hybrid_rerank">Hybrid + reranking</option></select></label><label>Evaluation run history<select aria-label="Evaluation run history" value={selected} onChange={e=>void read(e.target.value)}><option value="baseline">Preserved historical OpenAI baseline</option>{visible.map(r=><option key={r.run_id} value={r.run_id}>{r.label} | {r.created_at}</option>)}</select></label></div>
 {error&&<p role="alert" className="error">{error}</p>}{report?.available===false&&<div className="eval-empty"><h2>No saved evaluation yet</h2><p>{report.message}</p></div>}
 {report&&report.available!==false&&<><p className="run-info">{report.mode==='demo'?'OFFLINE DEMO - synthetic retrieval': 'OpenAI run'} | {report.examples} questions | K={report.top_k} | {report.updated_at||report.created_at}</p>
 <p className="run-info">{report.evaluation_kind==='retrieval_only'?'Retrieval only: no generated answer scores':'Answer evaluation'} | {report.retrieval_configuration?.mode||'dense'} | Chat: {report.chat_model} | Embeddings: {report.embedding_model}</p>
 {report.dataset_split&&<p className="run-info">Split: {report.dataset_split} | {report.answerable_examples} answerable / {report.unanswerable_examples} unanswerable | protocol {report.evaluation_protocol}</p>}
 {report.calibration_note&&<p className="method-note">{report.calibration_note}</p>}{report.embedding_note&&<p className="method-note">{report.embedding_note}</p>}
 {Object.values(report.judge_missing_counts||{}).some(n=>n>0)&&<p role="alert" className="error">Missing judge scores are excluded from averages. Inspect the raw report before comparing.</p>}
 <div className="metric-grid">{Object.entries(report.summary||{}).map(([key,value])=><article key={key}><h2>{key.replaceAll('_',' ')}</h2><strong>{formatted(key,value)}</strong>{!key.includes('seconds')&&key!=='selected_count'&&!key.includes('tokens')&&value!==null&&<meter aria-label={key} min={0} max={1} value={value}/>}<p>{explanations[key]}</p>{report.metric_denominators?.[key]!==undefined&&<small>Applicable examples: {report.metric_denominators[key]}</small>}</article>)}</div>
 <h2>Before and after</h2><p>Historical baseline versus selected run. Different datasets or prompts are not a controlled before/after comparison. Historical latency includes question embedding; ablations exclude a shared batch and optional judging. Compare held-out methods under their shared frozen protocol.</p>
 <div className="comparison-charts">{['source_recall_at_k','source_precision_at_k'].map(key=><article key={key}><h3>{key.replaceAll('_',' ')}</h3><label>Historical baseline <meter min={0} max={1} value={baseline?.summary?.[key]||0}/>{formatted(key,baseline?.summary?.[key])}</label><label>Selected run <meter min={0} max={1} value={report.summary?.[key]||0}/>{formatted(key,report.summary?.[key])}</label></article>)}</div>
 <div className="eval-table"><table><thead><tr><th>Metric</th><th>Historical baseline</th><th>Selected run</th></tr></thead><tbody>{Object.entries(report.summary||{}).map(([key,value])=><tr key={key}><td>{key.replaceAll('_',' ')}</td><td>{formatted(key,baseline?.summary?.[key])}</td><td>{formatted(key,value)}</td></tr>)}</tbody></table></div>
 <h2>Failure analysis</h2><p>{failures.length} review candidates: low source/evidence recall, missed strict abstention, invalid citations, or correctness/faithfulness/support judge below 0.8. These flags are heuristics.</p>{failures.map(r=><p key={r.question} className="error">{r.question}</p>)}
 <h2>Question results</h2><div className="eval-table question-results"><table><thead><tr><th>Question and reference</th><th>{report.evaluation_kind==='retrieval_only'?'Selected chunk IDs':'Generated answer'}</th><th>Latency</th><th>Valid citations</th></tr></thead><tbody>{report.results?.map((r,i)=><tr key={i}><td><b>{r.question}</b><p>{r.reference_answer}</p></td><td>{r.answer??r.selected_chunk_ids?.join(', ')??'No selected evidence'}</td><td><span className="latency-bar" style={{width:`${Math.max(2,Math.min(100,(r.latency_seconds??r.retrieval_seconds??0)*20))}%`}}/>{formatted('latency_seconds',r.latency_seconds??r.retrieval_seconds)}</td><td>{formatted('citation_validity',r.citation_validity)}</td></tr>)}</tbody></table></div></>}
 </main>;
}
