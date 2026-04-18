import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ClerkProvider } from '@clerk/clerk-react';
import { ThemeProvider } from './hooks/useTheme';
import { LanguageProvider } from './hooks/useLanguage';
import { ClerkAuthBridge } from './components/auth/ClerkAuthBridge';
import { CLERK_ENABLED, CLERK_PUBLISHABLE_KEY } from './lib/runtime';
import App from './App';
import './index.css';

function AppWithProviders() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <LanguageProvider>
          {CLERK_ENABLED && <ClerkAuthBridge />}
          <App />
        </LanguageProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

const root = createRoot(document.getElementById('root')!);

if (CLERK_ENABLED) {
  root.render(
    <StrictMode>
      <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY} afterSignOutUrl="/">
        <AppWithProviders />
      </ClerkProvider>
    </StrictMode>,
  );
} else {
  root.render(
    <StrictMode>
      <AppWithProviders />
    </StrictMode>,
  );
}
