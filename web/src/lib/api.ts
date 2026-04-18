import { AUTH_ENABLED, CLERK_ENABLED } from './runtime';

const API_BASE = '/api';
const TOKEN_STORAGE_KEY = 'hexmind-token';

// ─── Token management ─────────────────────────────────────
// For legacy local-JWT mode
let accessToken: string | null = AUTH_ENABLED ? localStorage.getItem(TOKEN_STORAGE_KEY) : null;

if (!AUTH_ENABLED) {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

// Clerk-mode token getter — injected by ClerkProvider wrapper at startup
let _clerkGetToken: (() => Promise<string | null>) | null = null;

/** Called once from ClerkAuthBridge to wire in Clerk's getToken. */
export function setClerkTokenGetter(fn: () => Promise<string | null>) {
  _clerkGetToken = fn;
}

function throwAuthDisabled(): never {
  throw new ApiError(403, 'Authentication is disabled in local mode');
}

export function setToken(token: string | null) {
  if (!AUTH_ENABLED) {
    accessToken = null;
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    return;
  }
  accessToken = token;
  if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
  else localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function getToken() {
  return AUTH_ENABLED ? accessToken : null;
}

// ─── Fetch wrapper ─────────────────────────────────────────
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  };

  // Prefer Clerk JWT, fall back to legacy local JWT
  if (CLERK_ENABLED && _clerkGetToken) {
    const clerkToken = await _clerkGetToken();
    if (clerkToken) headers['Authorization'] = `Bearer ${clerkToken}`;
  } else if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

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

export interface UIPreferences {
  ui_locale: 'zh' | 'en';
  theme_mode: 'light' | 'dark' | 'system';
}

export interface DiscussionPreferences {
  default_discussion_locale: 'zh' | 'en';
  default_selected_model_id: string | null;
  default_analysis_depth: 'quick' | 'standard' | 'deep' | null;
  default_execution_token_cap: number | null;
  default_discussion_max_rounds: number | null;
  default_time_budget_seconds: number | null;
}

export interface UserSettings {
  ui_preferences: UIPreferences;
  discussion_preferences: DiscussionPreferences;
  feature_flags: Record<string, boolean>;
}

export interface UserSettingsUpdate {
  ui_preferences?: Partial<UIPreferences>;
  discussion_preferences?: Partial<DiscussionPreferences>;
  feature_flags?: Record<string, boolean>;
}

export async function register(email: string, display_name: string, password: string) {
  if (!AUTH_ENABLED) {
    throwAuthDisabled();
  }
  const data = await request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, display_name, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function login(email: string, password: string) {
  if (!AUTH_ENABLED) {
    throwAuthDisabled();
  }
  const data = await request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function getMe() {
  if (!AUTH_ENABLED) {
    throwAuthDisabled();
  }
  return request<UserProfile>('/auth/me');
}

export async function getMySettings() {
  if (!AUTH_ENABLED) {
    throwAuthDisabled();
  }
  return request<UserSettings>('/auth/me/settings');
}

export async function updateMySettings(payload: UserSettingsUpdate) {
  if (!AUTH_ENABLED) {
    throwAuthDisabled();
  }
  return request<UserSettings>('/auth/me/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function logout() {
  setToken(null);
}

// ─── Discussions ───────────────────────────────────────────
export interface CreateDiscussionConfig {
  selected_model?: string;
  analysis_depth?: 'quick' | 'standard' | 'deep';
  execution_token_cap?: number;
  discussion_max_rounds?: number;
  time_budget_seconds?: number;
  discussion_locale?: 'zh' | 'en';
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

export interface ModelCapabilities {
  vision: boolean;
  tools: boolean;
  reasoning: boolean;
  max_output_mode: 'standard' | 'high_quality';
}

export interface ModelOption {
  id: string;
  label: string;
  capabilities: ModelCapabilities;
}

export interface AnalysisDepthOption {
  id: 'quick' | 'standard' | 'deep';
  max_personas: number;
  execution_token_cap: number;
  exploration_token_cap: number;
  finalization_reserve_token_cap: number;
  discussion_max_rounds: number;
  time_budget_seconds: number;
  supports_fork: boolean;
}

export interface DiscussionStatus {
  discussion_id: string;
  question: string;
  run_state: 'running' | 'completed';
  completion_status: 'converged' | 'partial' | 'cancelled' | 'error' | null;
  termination_reason: string | null;
  status: string;
  personas: string[];
  rounds_completed: number;
  token_used: number;
  execution_token_cap: number;
  exploration_token_cap: number;
  finalization_reserve_token_cap: number;
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

export interface AppSettings {
  default_model_id: string;
  models: ModelOption[];
  default_analysis_depth: 'quick' | 'standard' | 'deep';
  analysis_depths: AnalysisDepthOption[];
  plan_max_personas: number;
  default_execution_token_cap: number;
  default_discussion_max_rounds: number;
  default_time_budget_seconds: number;
  default_discussion_locale: 'zh' | 'en';
}

export async function getSettings() {
  return request<AppSettings>('/settings/');
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  selected_model?: string;
  messages: ChatMessage[];
  stream?: boolean;
}

export interface ChatResponse {
  selected_model: string;
  resolved_model: string;
  content: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  finish_reason: string;
}

export async function chat(payload: ChatRequest) {
  return request<ChatResponse>('/chat/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
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

// ─── Billing ───────────────────────────────────────────────
export interface PlanModelInfo {
  id: string;
  label: string;
}

export interface PlanFeature {
  text: string;
  text_zh: string;
}

export interface PricingPlan {
  id: string;
  name: string;
  name_zh: string;
  price_monthly: number;
  price_yearly: number;
  badge: string | null;
  badge_zh: string | null;
  description: string;
  description_zh: string;
  models: PlanModelInfo[];
  features: PlanFeature[];
  highlighted: boolean;
}

export interface BillingInfo {
  current_plan: string;
  discussions_used: number;
  discussions_limit: number | null;
  credits_remaining: number;
  credits_monthly: number;
  plan_execution_token_cap: number;
}

export async function getPlans() {
  return request<PricingPlan[]>('/billing/plans');
}

export async function getBillingInfo() {
  return request<BillingInfo>('/billing/info');
}
