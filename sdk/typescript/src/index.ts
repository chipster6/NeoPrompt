export interface ChooseRequest {
  assistant: string;
  category: string;
  raw: string;
  enhance?: boolean;
  force_json?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [k: string]: any;
}

export interface ChooseResponse {
  id?: string;
  decision_id?: string;
  engineered_prompt?: string;
  prompt?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [k: string]: any;
}

export interface FeedbackRequest {
  decision_id: string | number;
  reward: -1 | 0 | 1;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  components?: Record<string, any>;
}

export type HistoryResponse = unknown;

export interface ClientOptions {
  baseUrl?: string; // default http://localhost/api
  headers?: Record<string, string>;
  timeoutMs?: number; // reserved for future
}

const defaultBase = (typeof process !== 'undefined' && process.env?.NEOPROMPT_API_BASE) ?? "http://localhost/api";

export class Client {
  constructor(private opts: ClientOptions = {}) {}
  private base() { return this.opts.baseUrl ?? defaultBase; }
  private headers() { return { Accept: "application/json", ...(this.opts.headers ?? {}) }; }

  async health(): Promise<{ok: boolean}> {
    const r = await fetch(`${this.base()}/healthz`, { headers: this.headers() });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  async choose(req: ChooseRequest): Promise<ChooseResponse> {
    const r = await fetch(`${this.base()}/choose`, {
      method: "POST",
      headers: { ...this.headers(), "Content-Type": "application/json" },
      body: JSON.stringify({
        assistant: req.assistant,
        category: req.category,
        raw_input: req.raw,
        options: { enhance: !!req.enhance, force_json: !!req.force_json }
      }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  async feedback(req: FeedbackRequest): Promise<unknown> {
    const r = await fetch(`${this.base()}/feedback`, {
      method: "POST",
      headers: { ...this.headers(), "Content-Type": "application/json" },
      body: JSON.stringify({
        decision_id: req.decision_id,
        reward: req.reward,
        reward_components: req.components ?? {}
      }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  async history(params?: { limit?: number; assistant?: string; category?: string; with_text?: boolean }): Promise<HistoryResponse> {
    const q = new URLSearchParams();
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.assistant) q.set("assistant", params.assistant);
    if (params?.category) q.set("category", params.category);
    if (params?.with_text) q.set("with_text", "1");
    const r = await fetch(`${this.base()}/history?${q.toString()}`, { headers: this.headers() });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  async promptTemplates(): Promise<unknown> {
    const r = await fetch(`${this.base()}/prompt-templates`, { headers: this.headers() });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  async promptTemplatesSchema(): Promise<unknown> {
    const r = await fetch(`${this.base()}/prompt-templates/schema`, { headers: this.headers() });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }
}
