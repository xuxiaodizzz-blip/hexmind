// AUTH_ENABLED: legacy local-JWT flag (kept for backward compat, now unused in Clerk mode)
const rawAuthFlag = String(import.meta.env.VITE_HEXMIND_ENABLE_AUTH ?? '')
  .trim()
  .toLowerCase();

export const AUTH_ENABLED =
  rawAuthFlag === '1' ||
  rawAuthFlag === 'true' ||
  rawAuthFlag === 'yes' ||
  rawAuthFlag === 'on';

// CLERK_ENABLED: Clerk is active when publishable key is provided
export const CLERK_PUBLISHABLE_KEY =
  (import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined) ?? '';

export const CLERK_ENABLED = CLERK_PUBLISHABLE_KEY.startsWith('pk_');

// LOCAL_ONLY_MODE: no auth at all (used to show/hide the sidebar "Local Mode" badge)
export const LOCAL_ONLY_MODE = !AUTH_ENABLED && !CLERK_ENABLED;
