import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
const COOKIE = 'citerag_owner';
const backend = () => (process.env.CITERAG_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const failure = (detail: string, status: number) => NextResponse.json({ detail }, { status, headers: { 'Cache-Control': 'no-store' } });

async function boundedBody(request: NextRequest, limit: number) {
  const reader = request.body?.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  if (reader) while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > limit) { await reader.cancel(); throw new Error('body_limit'); }
    chunks.push(value);
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.length; }
  return body;
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path: parts } = await context.params;
  const path = parts.join('/');
  const mutation = request.method !== 'GET';
  // Same-origin BFF only; never forward browser-supplied Authorization/Host.
  const frontendOrigin = process.env.CITERAG_FRONTEND_ORIGIN || 'http://localhost:3000';
  if (mutation && request.headers.get('origin') !== frontendOrigin) return failure('Same-origin request required.', 403);
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const upstream = (url: string, init: RequestInit = {}) => fetch(`${backend()}/${url}`, { ...init, redirect: 'error', cache: 'no-store', signal: AbortSignal.timeout(180_000) });
  try {
    if (path === 'logout' && request.method === 'POST') {
      jar.delete(COOKIE);
      return NextResponse.json({ authenticated: false });
    }
    if (path === 'login' && request.method === 'POST') {
      const body = JSON.parse(new TextDecoder().decode(await boundedBody(request, 2048)));
      if (typeof body.token !== 'string' || body.token.length < 32 || body.token.length > 512) return failure('Enter the owner access token.', 401);
      const result = await upstream('auth', { headers: { Authorization: `Bearer ${body.token}` } });
      if (!result.ok) return failure('Owner sign-in failed or live mode is not configured.', result.status);
      jar.set(COOKIE, body.token, { httpOnly: true, secure: process.env.NODE_ENV === 'production' && process.env.CITERAG_LOCAL_HTTP !== 'true', sameSite: 'strict', path: '/', maxAge: 3600 });
      return NextResponse.json({ authenticated: true }, { headers: { 'Cache-Control': 'no-store' } });
    }
    const allowed = /^(health|session|retrieval\/config|showcase\/questions|documents(?:\/[a-zA-Z0-9-]+)?|chat|monitoring|evaluations(?:\/runs(?:\/[a-f0-9-]+)?)?)$/;
    if (!allowed.test(path) || !['GET', 'POST', 'DELETE'].includes(request.method)) return failure('Route unavailable.', 404);
    if (mutation && path !== 'chat') {
      const authenticated = await upstream('auth', { headers });
      if (!authenticated.ok) return failure('Owner authentication required.', authenticated.status);
    }
    const type = request.headers.get('content-type');
    if (type) headers['Content-Type'] = type;
    const body = request.method === 'POST' ? await boundedBody(request, path === 'documents' ? 21 * 1024 * 1024 : 32 * 1024) : undefined;
    const result = await upstream(path, { method: request.method, headers, body });
    return new NextResponse(result.body, { status: result.status, headers: { 'Content-Type': result.headers.get('content-type') || 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
  } catch (error) {
    return failure(error instanceof Error && error.message === 'body_limit' ? 'Request body too large.' : 'Backend request failed. Check service configuration.', error instanceof Error && error.message === 'body_limit' ? 413 : 502);
  }
}
export const GET = proxy;
export const POST = proxy;
export const DELETE = proxy;
