/**
 * ClerkAuthBridge
 *
 * Wires Clerk's getToken into the api.ts fetch wrapper, so every API call
 * automatically attaches the Clerk session JWT — no manual token management.
 *
 * Render this component once, inside <ClerkProvider>, near the root.
 */
import { useAuth } from '@clerk/clerk-react';
import { useEffect } from 'react';
import { setClerkTokenGetter } from '../../lib/api';

export function ClerkAuthBridge() {
  const { getToken, isLoaded } = useAuth();

  useEffect(() => {
    if (!isLoaded) return;
    // Register an async getter that always returns a fresh token.
    setClerkTokenGetter(() => getToken());
  }, [getToken, isLoaded]);

  return null;
}
