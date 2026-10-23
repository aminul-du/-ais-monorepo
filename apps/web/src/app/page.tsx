'use client';
import { useEffect, useState } from 'react';
import { colors, radius, font } from '@mcore/design-system';

type Status = 'loading' | 'ok' | 'error';
type State = { status: Status; data?: Record<string, unknown>; error?: string };

export default function Home() {
  const [ai, setAi] = useState<State>({ status: 'loading' });
  const [core, setCore] = useState<State>({ status: 'loading' });
  useEffect(() => {
    fetch('/api/healthz').then(r => r.json()).then(data => setAi({ status: 'ok', data })).catch(e => setAi({ status: 'error', error: String(e) }));
    fetch('/core/healthz').then(r => r.json()).then(data => setCore({ status: 'ok', data })).catch(e => setCore({ status: 'error', error: String(e) }));
  }, []);
  return (
    <main style={{ padding: 40, fontFamily: font.sans, background: colors.bg, color: colors.textPrimary, minHeight: '100vh' }}>
      <h1 style={{ color: colors.accent, margin: 0 }}>MCore</h1>
      <p style={{ color: colors.textSecondary, marginTop: 4 }}>Engineering Intelligence for the World.</p>
      <div style={{ marginTop: 40, display: 'grid', gap: 16, maxWidth: 640 }}>
        <Panel title="AI Orchestrator (/api)" state={ai} />
        <Panel title="Core API (/core)" state={core} />
      </div>
    </main>
  );
}
function Panel({ title, state }: { title: string; state: State }) {
  const color = state.status === 'ok' ? colors.statusOk : state.status === 'error' ? colors.statusError : colors.statusWarn;
  const body = state.status === 'loading' ? 'loading...' : state.status === 'error' ? state.error : JSON.stringify(state.data, null, 2);
  return (
    <div style={{ background: colors.surface, borderRadius: radius.md, padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ color: colors.textSecondary, fontSize: 12 }}>{title}</span>
        <span style={{ fontSize: 12, color }}>{state.status}</span>
      </div>
      <pre style={{ margin: 0, fontFamily: font.mono, fontSize: 13, whiteSpace: 'pre-wrap' }}>{body}</pre>
    </div>
  );
}
