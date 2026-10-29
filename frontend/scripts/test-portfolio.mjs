// Build first. Runs both access modes using isolated, loopback-only fixtures.
import {spawn, execFileSync} from 'node:child_process';
import {mkdirSync, cpSync, openSync, closeSync, existsSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(frontend);
const work = path.join(root, '.work', 'browser-verification');
mkdirSync(work, {recursive:true});
mkdirSync(path.join(frontend, '.next/standalone/.next/static'), {recursive:true});
cpSync(path.join(frontend, '.next/static'), path.join(frontend, '.next/standalone/.next/static'), {recursive:true});
const venv = path.join(root, 'backend/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.CITERAG_TEST_PYTHON || (existsSync(venv) ? venv : 'python');
const children = [];
const logs = [];
function start(command, args, cwd, env, label) {
  const fd = openSync(path.join(work, label + '.log'), 'w');
  logs.push(fd);
  const child = spawn(command, args, {cwd, env:{...process.env, OPENAI_API_KEY:'', ...env}, stdio:['ignore',fd,fd], windowsHide:true});
  child.on('error', error => console.error(`${label}: ${error.message}`));
  children.push(child);
  return child;
}
async function ready(url, mode) {
  for (let i=0; i<60; i++) {
    try {const response=await fetch(url, {signal:AbortSignal.timeout(2000)});if(response.ok && (await response.json()).access_mode===mode)return;} catch {}
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  throw new Error('Fixture did not become ready; inspect ignored .work/browser-verification logs.');
}
function stop() {
  for(const child of children.splice(0))child.kill();
  for(const fd of logs.splice(0))closeSync(fd);
}
try {
  for (const mode of ['showcase','live']) {
    const apiPort = mode==='showcase'?8010:8011;
    const uiPort = mode==='showcase'?3010:3011;
    start(python,['scripts/serve_browser_fixture.py','--mode',mode,'--port',String(apiPort),'--data',path.join(work,mode)],path.join(root,'backend'),{},`${mode}-api`);
    start(process.execPath,['.next/standalone/server.js'],frontend,{HOSTNAME:'127.0.0.1',PORT:String(uiPort),CITERAG_BACKEND_URL:`http://127.0.0.1:${apiPort}`,CITERAG_FRONTEND_ORIGIN:`http://127.0.0.1:${uiPort}`,CITERAG_LOCAL_HTTP:'true'},`${mode}-frontend`);
    await ready(`http://127.0.0.1:${uiPort}/api/session`,mode);
    const specs = mode==='showcase' ? ['tests/showcase.spec.ts','tests/evaluations.spec.ts','tests/evaluation-race.spec.ts'] : ['tests/auth.spec.ts','tests/workspace.spec.ts','tests/evaluations.spec.ts','tests/evaluation-race.spec.ts'];
    execFileSync(process.execPath,['node_modules/@playwright/test/cli.js','test',...specs],{cwd:frontend,stdio:'inherit',env:{...process.env,OPENAI_API_KEY:'',CITERAG_TEST_MODE:'demo',CITERAG_TEST_OWNER:mode==='live'?'true':'false',CITERAG_TEST_SHOWCASE:mode==='showcase'?'true':'false',CITERAG_TEST_FRONTEND_URL:`http://127.0.0.1:${uiPort}`,CITERAG_TEST_BACKEND_URL:`http://127.0.0.1:${apiPort}`}});
    stop();
  }
} finally {stop();}
