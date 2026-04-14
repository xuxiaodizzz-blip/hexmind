const API_BASE = '/api';

// ─── Token management ─────────────────────────────────────
let accessToken: string | null = localStorage.getItem('hexmind-token');

export function setToken(token: string | null) {
  accessToken = token;
  if (token) localStorage.setItem('hexmind-token', token);
  else localStorage.removeItem('hexmind-token');
}

export function getToken() {
  return accessToken;
}

// ─── Fetch wrapper ─────────────────────────────────────────
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  };
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? body.message ?? 'Request failed');
  }
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

// ─── Auth ──────────────────────────────────────────────────
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export async function register(email: string, display_name: string, password: string) {
  const data = await request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, display_name, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function login(email: string, password: string) {
  const data = await request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function getMe() {
  return request<UserProfile>('/auth/me');
}

export function logout() {
  setToken(null);
}

// ─── Discussions ───────────────────────────────────────────
export interface CreateDiscussionConfig {
  model?: string;
  token_budget?: number;
  locale?: 'zh' | 'en';
}

export interface CreateDiscussionPayload {
  question: string;
  persona_ids: string[];
  config?: CreateDiscussionConfig;
}

export interface CreateDiscussionResponse {
  discussion_id: string;
  status: string;
}

export interface DiscussionStatus {
  discussion_id: string;
  question: string;
  status: string;
  personas: string[];
  rounds_completed: number;
  token_used: number;
  token_budget: number;
}

export async function createDiscussion(payload: CreateDiscussionPayload) {
  return request<CreateDiscussionResponse>('/discussions/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getDiscussionStatus(id: string) {
  return request<DiscussionStatus>(`/discussions/${id}`);
}

export function streamDiscussion(id: string, lastEventId?: string) {
  const url = `${API_BASE}/discussions/${id}/stream`;
  const es = new EventSource(url);
  // Note: EventSource doesn't support custom headers.
  // For auth, the backend uses require_user_if_db_enabled which allows None.
  // In production, consider switching to fetch-based SSE or token in query param.
  return es;
}

// ─── Archive ───────────────────────────────────────────────
export interface ArchiveSummary {
  id: string;
  question: string;
  created_at: string;
  status: string;
  personas: string[];
  verdict: string | null;
  confidence: string | null;
}

export interface ArchiveListResponse {
  total: number;
  items: ArchiveSummary[];
}

export async function getArchive(params?: { query?: string; limit?: number; offset?: number }) {
  const sp = new URLSearchParams();
  if (params?.query) sp.set('query', params.query);
  if (params?.limit) sp.set('limit', String(params.limit));
  if (params?.offset) sp.set('offset', String(params.offset));
  const qs = sp.toString();
  return request<ArchiveListResponse>(`/archive/${qs ? '?' + qs : ''}`);
}

// ─── Personas ──────────────────────────────────────────────
export interface PersonaSummary {
  id: string;
  name: string;
  domain: string;
  description: string;
}

export interface PersonaDetail extends PersonaSummary {
  prompt: string;
}

export async function getPersonas(domain?: string) {
  const qs = domain ? `?domain=${encodeURIComponent(domain)}` : '';
  return request<PersonaSummary[]>(`/personas/${qs}`);
}

export async function getPersona(id: string) {
  return request<PersonaDetail>(`/personas/${encodeURIComponent(id)}`);
}

export interface PromptSummary {
  id: string;
  name: string;
  position: string;
  domain: string;
  kind: string;
  hat: string | null;
  hat_context: string;
  applicable_hats: string[];
  status: string;
  source: string;
  description: string;
}

export interface PromptDetail extends PromptSummary {
  prompt: string;
  prompt_mode: string;
  tags: string[];
  source_title: string;
  source_path: string;
}

export async function getPrompts(params?: {
  position?: string;
  domain?: string;
  kind?: string;
  hat?: string;
  status?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.position) sp.set('position', params.position);
  if (params?.domain) sp.set('domain', params.domain);
  if (params?.kind) sp.set('kind', params.kind);
  if (params?.hat) sp.set('hat', params.hat);
  if (params?.status) sp.set('status', params.status);
  const qs = sp.toString();
  return request<PromptSummary[]>(`/prompts/${qs ? '?' + qs : ''}`);
}

export async function getPrompt(id: string) {
  return request<PromptDetail>(`/prompts/${encodeURIComponent(id)}`);
}
