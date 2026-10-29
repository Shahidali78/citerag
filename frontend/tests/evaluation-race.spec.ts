import {test,expect} from '@playwright/test';

test('latest selected evaluation wins when older requests finish later',async({page})=>{
 const API='**/api';
 const older='11111111-1111-4111-8111-111111111111';
 const newer='22222222-2222-4222-8222-222222222222';
 const base={available:true,mode:'openai',examples:1,top_k:5,summary:{source_recall_at_k:1},results:[{question:'Baseline example',answer:'Baseline answer'}]};
 await page.route(`${API}/evaluations`,route=>route.fulfill({json:base}));
 await page.route(`${API}/evaluations/runs`,route=>route.fulfill({json:[{run_id:older,label:'Older request',retrieval_configuration:{mode:'dense'}},{run_id:newer,label:'New selected request',retrieval_configuration:{mode:'dense'}}]}));
 await page.route(`${API}/evaluations/runs/*`,async route=>{
  const old=route.request().url().endsWith(older);
  if(old)await new Promise(resolve=>setTimeout(resolve,600));
  await route.fulfill({json:{...base,results:[{question:old?'Stale result':'Latest selected result',answer:'Saved answer'}]}});
 });
 await page.goto('/evaluations');
 await expect(page.locator('.question-results')).toContainText('Baseline example');
 const delayed=page.waitForResponse(`${API}/evaluations/runs/${older}`);
 await page.getByLabel('Evaluation run history').selectOption(older);
 await page.getByLabel('Evaluation run history').selectOption(newer);
 await delayed;
 await expect(page.locator('.question-results')).toContainText('Latest selected result');
 await expect(page.getByLabel('Evaluation run history')).toHaveValue(newer);
});
