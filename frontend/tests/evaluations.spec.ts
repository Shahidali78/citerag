const backend = process.env.CITERAG_TEST_BACKEND_URL || 'http://localhost:8000';
import { test, expect } from '@playwright/test';

test('dashboard displays the saved run and its real metrics', async ({ page, request }) => {
  let report = await (await request.get(`${backend}/evaluations`)).json();
  const history=await (await request.get(`${backend}/evaluations/runs`)).json();
  const heldout=history.find((r:{dataset_split?:string;retrieval_configuration?:{mode:string}})=>r.dataset_split==='held_out'&&r.retrieval_configuration?.mode==='hybrid_rerank');
  if(heldout)report=await (await request.get(`${backend}/evaluations/runs/${heldout.run_id}`)).json();
  test.skip(report.available===false, 'No saved evaluation to inspect');
  await page.goto('/evaluations');
  await expect(page.getByRole('heading', { name: 'Evaluation dashboard' })).toBeVisible();
  if(heldout){await page.getByLabel('Evaluation run history').selectOption(heldout.run_id);await expect(page.getByText('Split: held_out',{exact:false})).toBeVisible();}
  await expect(page.locator('.run-info').first()).toContainText(report.mode === 'openai' ? 'OpenAI run' : 'OFFLINE DEMO');
  await expect(page.locator('.run-info').first()).toContainText(`${report.examples} questions`);
  await expect(page.locator('.question-results tbody tr')).toHaveCount(report.examples);
  const recall = page.locator('.metric-grid article').filter({ has: page.getByRole('heading', { name: 'source recall at k', exact: true }) });
  await expect(recall.locator('strong')).toHaveText(`${(report.summary.source_recall_at_k * 100).toFixed(1)}%`);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: `test-results/evaluations-${test.info().project.name}.png`, fullPage: true });
  const runs=await (await request.get(`${backend}/evaluations/runs`)).json();
  const dense=runs.find((r:{evaluation_kind:string;retrieval_configuration?:{mode:string}})=>r.evaluation_kind==='retrieval_only'&&r.retrieval_configuration?.mode==='dense');
  const initial=runs.find((r:{label:string})=>r.label==='Answers: hybrid_rerank');
  if(initial){await page.getByLabel('Evaluation retrieval configuration').selectOption('hybrid_rerank');await page.getByLabel('Evaluation run history').selectOption(initial.run_id);await expect(page.locator('.error').filter({hasText:'Does this project isolate multiple user accounts?'})).toBeVisible();}
  if(dense){await page.getByLabel('Evaluation retrieval configuration').selectOption('dense');await page.getByLabel('Evaluation run history').selectOption(dense.run_id);await expect(page.locator('.run-info').nth(1)).toContainText('Retrieval only');}
});
