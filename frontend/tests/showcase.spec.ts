import {test, expect} from '@playwright/test';

test.beforeEach(() => test.skip(process.env.CITERAG_TEST_SHOWCASE !== 'true', 'Requires isolated showcase fixture'));

test('public showcase replays an example and opens actual saved evidence', async ({page, request}) => {
  await page.goto('/');
  await expect(page.getByRole('region', {name:'Access mode'})).toContainText('Public showcase');
  await expect(page.getByText('Saved showcase', {exact:true})).toBeVisible();
  await expect(page.locator('.sample-questions button')).toHaveCount(4);
  const question = await page.locator('.sample-questions button').first().innerText();
  await page.locator('.sample-questions button').first().click();
  await expect(page.locator('.message.user')).toContainText(question);
  await expect(page.locator('.message.assistant .citation-pill').first()).toBeVisible();
  await page.locator('.message.assistant .citation-pill').first().click();
  await expect(page.getByRole('dialog').locator('.chunk-id')).not.toBeEmpty();
  await page.keyboard.press('Escape');
  await expect(page.locator('input[type=file]')).toBeDisabled();
  await expect(page.getByRole('button', {name:'Delete verification.pdf', exact:true})).toBeDisabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  const response = await request.get('/api/evaluations');
  expect((await response.json()).examples).toBe(40);
  await page.goto('/monitoring');
  await expect(page.locator('.private-monitoring')).toContainText('does not display private activity');
});

test('showcase denies mutations and private monitoring through both servers', async ({request,baseURL}) => {
  const backend = process.env.CITERAG_TEST_BACKEND_URL!;
  expect((await request.post(`${backend}/documents`)).status()).toBe(403);
  expect((await request.delete(`${backend}/documents/anything`)).status()).toBe(403);
  expect((await request.get(`${backend}/monitoring`)).status()).toBe(403);
  expect((await request.get('/api/monitoring')).status()).toBe(403);
  expect((await request.post('/api/documents', {headers:{Origin:baseURL!}})).status()).toBe(403);
  expect((await request.post('/api/chat', {headers:{Origin:baseURL!},data:{question:'Invent an answer'}})).status()).toBe(422);
});
