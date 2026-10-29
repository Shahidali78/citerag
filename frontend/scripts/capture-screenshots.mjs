// Capture public sample UI only. No chat submission or paid API calls.
import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
await mkdir('../docs/screenshots', { recursive: true });
const browser = await chromium.launch();
try {
  for (const [name, viewport] of [['desktop', { width: 1440, height: 1000 }], ['mobile', { width: 390, height: 844 }]]) {
    const page = await browser.newPage({ viewport });
    for (const [label, route] of [['workspace', '/'], ['evaluations', '/evaluations'], ['monitoring', '/monitoring']]) {
      await page.goto(`http://localhost:3000${route}`);
      if (label === 'workspace') await page.getByLabel('Ask your documents').waitFor();
      else await page.locator('.metric-grid article').first().waitFor();
      await page.screenshot({ path: `../docs/screenshots/${label}-${name}.png`, fullPage: false });
    }
    await page.close();
  }
} finally { await browser.close(); }
