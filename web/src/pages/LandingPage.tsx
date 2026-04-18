// Deprecated: Marketing content moved to web-landing/ (Next.js at hexmind.ai).
import { useEffect } from 'react';

export default function LandingPage() {
  useEffect(() => {
    window.location.replace('https://hexmind.ai');
  }, []);
  return null;
}
