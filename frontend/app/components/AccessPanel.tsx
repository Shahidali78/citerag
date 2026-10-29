'use client';
import { useEffect, useState } from 'react';

export default function AccessPanel() {
  const [session, setSession] = useState<{access_mode: string; authenticated: boolean; provider_mode: string} | null>(null);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { fetch('/api/session', {cache: 'no-store'}).then(r => r.json()).then(setSession).catch(() => setError('Cannot connect to the backend.')); }, []);
  async function submit(signOut = false) {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/${signOut ? 'logout' : 'login'}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Sign-in failed');
      setToken(''); window.location.reload();
    } catch (e) { setError(e instanceof Error ? e.message : 'Sign-in failed'); }
    finally { setBusy(false); }
  }
  if (!session) return <div className="access-banner" role="status">{error || 'Connecting to workspace…'}</div>;
  return <div className="access-banner" role="region" aria-label="Access mode">
    {session?.access_mode === 'showcase' ? <p><strong>Public showcase</strong> · Saved sample responses and genuine evaluation reports. No new OpenAI calls. Uploads and monitoring are private.</p>
      : session?.authenticated ? <><p><strong>Owner live mode</strong> · {session.provider_mode === 'demo' ? 'Offline fixture provider; no OpenAI calls.' : 'New answers use OpenAI and your configured daily allowance.'}</p><button onClick={() => void submit(true)} disabled={busy}>Sign out</button></>
      : <form onSubmit={e => {e.preventDefault(); void submit();}}><strong>Protected live workspace</strong><label>Owner access token<input aria-label="Owner access token" type="password" autoComplete="current-password" maxLength={512} value={token} onChange={e => setToken(e.target.value)}/></label><button disabled={busy || !token}>{busy ? 'Signing in…' : 'Sign in'}</button></form>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
