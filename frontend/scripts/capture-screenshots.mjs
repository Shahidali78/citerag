// Capture public sample UI only. No chat submission or paid API calls.
import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
await mkdir('../docs/screenshots', { recursive: true });
const browser = await chromium.launch();
try {
  const check = await browser.newContext();
  const session = await (await check.request.get('http://localhost:3000/api/session')).json();
  await check.close();
  if (session.access_mode !== 'showcase') throw new Error('Capture only public showcase artifacts; private live screenshots are disabled.');
  for (const [name, viewport] of [['desktop', { width: 1440, height: 1000 }], ['mobile', { width: 390, height: 844 }]]) {
    const page = await browser.newPage({ viewport });
    for (const [label, route] of [['workspace', '/'], ['evaluations', '/evaluations'], ['monitoring', '/monitoring']]) {
      await page.goto(`http://localhost:3000${route}`);
      if (label === 'workspace') {
        await page.getByText('Saved showcase', {exact:true}).waitFor();
        await page.locator('.doc-name').first().waitFor();
        await page.locator('.sample-questions button').first().waitFor();
      }
      else if (label === 'monitoring') await page.locator('.private-monitoring').waitFor();
      else await page.locator('.metric-grid article').first().waitFor();
      await page.screenshot({ path: `../docs/screenshots/${label}-${name}.png`, fullPage: label === 'workspace' && name === 'mobile' });
    }
    await page.close();
  }
} finally { await browser.close(); }
