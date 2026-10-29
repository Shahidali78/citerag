import {test,expect} from '@playwright/test';

test.beforeEach(() => test.skip(process.env.CITERAG_TEST_OWNER !== 'true', 'Requires isolated authenticated fixture'));

test('owner sign-in uses an HttpOnly cookie and logout removes access', async ({page,context,baseURL}) => {
  const request = context.request;
  await context.clearCookies();
  await page.goto('/');
  await expect(page.getByLabel('Owner access token')).toBeVisible();
  expect((await request.get('/api/documents')).status()).toBe(401);
  await page.getByLabel('Owner access token').fill('wrong-but-long-enough-fixture-token-value');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('region',{name:'Access mode'}).getByRole('alert')).toContainText('sign-in failed');
  await page.getByLabel('Owner access token').fill('fixture-only-owner-token-not-for-deployment');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('region',{name:'Access mode'})).toContainText('Owner live mode');
  const cookie=(await context.cookies()).find(c=>c.name==='citerag_owner');
  expect(cookie?.httpOnly).toBe(true);expect(cookie?.sameSite).toBe('Strict');
  expect(await page.evaluate(()=>document.cookie)).not.toContain('citerag_owner');
  expect((await request.get('/api/documents')).status()).toBe(200);
  expect((await request.post('/api/chat',{headers:{Origin:'https://attacker.invalid'},data:{question:'bad origin'}})).status()).toBe(403);
  expect((await request.post('/api/chat',{headers:{Origin:baseURL!},data:{question:'What is the maximum upload size?'}})).status()).toBe(200);
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await expect(page.getByLabel('Owner access token')).toBeVisible();
  expect((await request.get('/api/documents')).status()).toBe(401);
});
