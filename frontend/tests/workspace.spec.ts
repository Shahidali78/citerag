const backend = process.env.CITERAG_TEST_BACKEND_URL || 'http://localhost:8000';
import { test, expect } from '@playwright/test';

const live = process.env.CITERAG_TEST_MODE === 'openai';
test.beforeEach(async ({ request }) => {
  const health = await (await request.get(`${backend}/health`)).json();
  expect(health.mode, 'Live tests require explicit CITERAG_TEST_MODE=openai to authorize API calls').toBe(live ? 'openai' : 'demo');
});

test('upload, ask, inspect evidence, copy, clear and delete', async ({ page, request }) => {
  const docs = await (await request.get(`${backend}/documents`)).json();
  for (const doc of docs) if (doc.filename === 'browser-guide.txt') await request.delete(`${backend}/documents/${doc.id}`);
  await page.goto('/');
  await expect(page.getByText(live ? 'OpenAI configured' : 'Offline demo', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: `test-results/workspace-${test.info().project.name}.png`, fullPage: true });
  await page.locator('input[type=file]').setInputFiles({ name: 'browser-guide.txt', mimeType: 'text/plain', buffer: Buffer.from('The browser test project uses emerald green buttons. The maximum upload size is 20 MB per file.') });
  await expect(page.getByText('browser-guide.txt', {exact:true})).toBeVisible();
  await page.getByLabel('Ask your documents').fill('What color are the browser test project buttons?');
  await page.getByRole('button', {name:'Send question'}).click();
  await expect(page.locator('.message.assistant')).toContainText('emerald green');
  await expect(page.locator('.retrieval-diagnostics')).toContainText('Retrieval diagnostics');
  await page.locator('.citation-pill').first().click();
  await expect(page.getByRole('dialog')).toContainText('not factual correctness');
  await expect(page.getByRole('dialog').locator('.chunk-id')).not.toBeEmpty();
  await page.getByRole('button', {name:'Close evidence'}).click();
  await page.getByRole('button', {name:'Copy answer'}).click();
  await expect(page.getByRole('button', {name:'Copied'}).or(page.locator('.error[role=alert]'))).toBeVisible();
  await page.getByRole('button', {name:/New conversation/}).click();
  await expect(page.locator('.message')).toHaveCount(0);
  await page.getByRole('button', {name:'Delete browser-guide.txt',exact:true}).click();
  await expect(page.locator('.doc-name').filter({hasText:'browser-guide.txt'})).toHaveCount(0);
  await page.getByRole('link', {name:/View evaluations/}).click();
  await expect(page.getByRole('heading',{name:'Evaluation dashboard'})).toBeVisible();
});

test('retrieval settings, diagnostics, and monitoring controls', async ({page,request}) => {
  const configuration=await (await request.get(`${backend}/retrieval/config`)).json();
  let payload: {retrieval_mode?:string;candidate_count?:number;relevance_threshold?:number}={};
  await page.route('**/chat',route=>{
    payload=route.request().postDataJSON();
    return route.fulfill({json:{answer:'The supported fact is 20 MB [1].',citations:[{marker:'[1]',chunk_id:'x:0',document_id:'x',filename:'fixture.txt',page:1,snippet:'20 MB',similarity:.7}],retrieved_count:1,
      diagnostics:[{chunk_id:'x:0',filename:'fixture.txt',page:1,vector_similarity:.7,keyword_score:2.5,fusion_rank:1,rerank_score:.8,selected:true}],telemetry:{request_id:'test-request'}}});
  });
  await page.goto('/');
  await page.getByText('Search settings',{exact:true}).click();
  await expect(page.getByLabel('Retrieval method')).toHaveValue(configuration.default.mode);
  await page.getByLabel('Retrieval method').selectOption('hybrid');
  await page.getByLabel('Candidate pool').fill('9');
  await page.getByLabel('Relevance threshold').fill('0.3');
  await page.getByLabel('Ask your documents').fill('Check settings');
  await page.getByRole('button',{name:'Send question'}).click();
  await expect(page.locator('.message.assistant')).toContainText('supported fact');
  expect(payload).toMatchObject({retrieval_mode:'hybrid',candidate_count:9,relevance_threshold:.3});
  await page.locator('.retrieval-diagnostics summary').click();
  await expect(page.locator('.retrieval-diagnostics')).toContainText('2.500');
  await page.getByRole('link',{name:'Monitoring',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Monitoring',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Total requests',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Refresh monitoring'}).click();
  await expect(page.locator('.metric-grid')).toContainText('Estimated API cost');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({path:`test-results/monitoring-${test.info().project.name}.png`,fullPage:true});
});

test('error handling and safe Markdown citations', async ({ page }) => {
  await page.route('**/chat', route => route.fulfill({json:{answer:'**Grounded** claim [1] <script>window.hacked=true</script> [unsafe](javascript:alert(1))',citations:[{marker:'[1]',chunk_id:'test:0',document_id:'test',filename:'test.md',page:1,snippet:'Grounded claim',similarity:0.8}],retrieved_count:1}}));
  await page.goto('/');
  await page.getByLabel('Ask your documents').fill('Test markdown');
  await page.getByRole('button',{name:'Send question'}).click();
  await expect(page.locator('.message-text strong')).toHaveText('Grounded');
  await expect(page.locator('.message-text script')).toHaveCount(0);
  await expect(page.locator('.message-text a[href^="javascript:"]')).toHaveCount(0);
  await page.locator('.citation-pill').click();
  await expect(page.getByRole('dialog')).toContainText('Grounded claim');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.unroute('**/chat');
  await page.route('**/chat',route=>route.fulfill({status:502,json:{detail:'Test provider unavailable'}}));
  await page.getByLabel('Ask your documents').fill('Try again');
  await page.getByRole('button',{name:'Send question'}).click();
  await expect(page.locator('.error[role=alert]')).toContainText('Test provider unavailable');
});

test('drag and drop upload and unsupported file error', async ({ page, request }) => {
  const docs = await (await request.get(`${backend}/documents`)).json();
  for (const doc of docs) if (doc.filename === 'drop-test.txt') await request.delete(`${backend}/documents/${doc.id}`);
  await page.goto('/');
  await page.locator('input[type=file]').setInputFiles({name:'bad.exe',mimeType:'application/octet-stream',buffer:Buffer.from('invalid')});
  await expect(page.locator('.error[role=alert]')).toContainText('Only PDF');
  await page.locator('.dropzone').evaluate(node => {
    const data = new DataTransfer();
    data.items.add(new File(['Drag and drop creates an indexed document.'],'drop-test.txt',{type:'text/plain'}));
    node.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:data}));
  });
  await expect(page.getByText('drop-test.txt',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Delete drop-test.txt',exact:true}).click();
  await expect(page.locator('.doc-name').filter({hasText:'drop-test.txt'})).toHaveCount(0);
});
