/**
 * TurnstileWidget
 *
 * Renders the Cloudflare Turnstile challenge widget and verifies the token
 * server-side before reporting success to the parent.
 *
 * Usage:
 *   <TurnstileWidget onVerified={(ok) => setTurnstileOk(ok)} />
 *
 * The widget is invisible / non-interactive by default (managed challenge).
 * Set VITE_TURNSTILE_SITE_KEY in your .env to enable it.
 * When the key is absent (local dev), onVerified(true) is called immediately.
 */
import { useEffect } from 'react';
import { Turnstile } from '@marsidev/react-turnstile';

const SITE_KEY = (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined) ?? '';

interface Props {
  onVerified: (success: boolean) => void;
}

export function TurnstileWidget({ onVerified }: Props) {
  // Local dev: Turnstile not configured — pass automatically
  useEffect(() => {
    if (!SITE_KEY) {
      onVerified(true);
    }
  }, [onVerified]);

  if (!SITE_KEY) return null;

  async function handleSuccess(token: string) {
    try {
      const res = await fetch('/api/turnstile/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });
      const data = await res.json();
      onVerified(data.success === true);
    } catch {
      onVerified(false);
    }
  }

  return (
    <Turnstile
      siteKey={SITE_KEY}
      onSuccess={handleSuccess}
      onError={() => onVerified(false)}
      onExpire={() => onVerified(false)}
      options={{ theme: 'dark', size: 'normal' }}
    />
  );
}
