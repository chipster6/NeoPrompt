// Vite injects import.meta.env at build-time; declare a minimal type for TS
declare const importMeta: { env: Record<string, string | undefined> };
const _env = (typeof import.meta !== 'undefined' ? (import.meta as any).env : (globalThis as any).importMeta?.env) || {};
export const API_BASE = _env.VITE_API_BASE || '/api';

export async function apiChoose(payload: {
  assistant: string;
  category: string;
  raw_input: string;
  options?: Record<string, any>;
  context_features?: Record<string, any>;
}) {
  const res = await fetch(`${API_BASE}/choose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Choose failed');
  return res.json();
}

export async function apiFeedback(payload: {
  decision_id: string;
  reward_components: Record<string, number>;
  reward: number;
  safety_flags?: string[];
}) {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Feedback failed');
  return res.json();
}

export async function apiHistory(params: { limit?: number; assistant?: string; category?: string; with_text?: boolean } = {}) {
  const url = new URL(`${API_BASE}/history`);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  });
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('History failed');
  return res.json();
}

export async function apiRecipes(reload?: boolean) {
  const url = new URL(`${API_BASE}/recipes`);
  if (reload) url.searchParams.set('reload', '1');
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Recipes failed');
  return res.json();
}

export async function apiStatsGet(params: { assistant?: string; category?: string } = {}) {
  const url = new URL(`${API_BASE}/stats`);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  });
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Stats fetch failed');
  return res.json();
}

export async function apiStatsUpdate(payload: { epsilon?: number; reset?: boolean; assistant?: string; category?: string }) {
  const res = await fetch(`${API_BASE}/stats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Stats update failed');
  return res.json();
}

