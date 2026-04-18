import { SignIn } from '@clerk/clerk-react';

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-[#0b0f17] flex items-center justify-center px-4 relative">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#00e5ff]/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#b499ff]/10 rounded-full blur-[120px]" />
      </div>
      <div className="relative z-10">
        <SignIn
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
          fallbackRedirectUrl="/"
          appearance={{
            variables: {
              colorPrimary: '#00e5ff',
              colorBackground: '#0e131d',
              colorInputBackground: '#151a23',
              colorText: '#ffffff',
              colorTextSecondary: 'rgba(255,255,255,0.5)',
              colorInputText: '#ffffff',
              colorNeutral: '#ffffff',
              borderRadius: '12px',
              fontFamily: 'inherit',
            },
            elements: {
              card: 'shadow-[0_0_60px_rgba(0,229,255,0.08)] border border-white/10',
              formButtonPrimary:
                'bg-[#00e5ff] text-black font-bold hover:bg-[#00cce6] transition-colors',
              footerActionLink: 'text-[#00e5ff] hover:text-[#00cce6]',
              headerTitle: 'text-white',
              headerSubtitle: 'text-white/50',
              socialButtonsBlockButton:
                'border border-white/10 bg-[#151a23] text-white hover:bg-white/5',
            },
          }}
        />
      </div>
    </div>
  );
}
