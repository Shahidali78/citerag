import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: process.env.CITERAG_TEST_FRONTEND_URL || 'http://localhost:3000', trace: 'retain-on-failure',
    ...(process.env.CITERAG_TEST_OWNER === 'true' ? {
      extraHTTPHeaders: {Authorization: 'Bearer fixture-only-owner-token-not-for-deployment'},
      storageState: {cookies: [{name:'citerag_owner', value:'fixture-only-owner-token-not-for-deployment', domain:'127.0.0.1', path:'/', expires:-1, httpOnly:true, secure:false, sameSite:'Strict' as const}], origins:[]},
    } : {}),
  },
  projects: [{ name: 'desktop', use: { ...devices['Desktop Chrome'] } }, { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } }],
});
