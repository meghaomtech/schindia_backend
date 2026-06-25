import type { ReactNode } from 'react';

interface AuthLayoutProps {
  title: string;
  children: ReactNode;
  footer: ReactNode;
}

export function AuthLayout({ title, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-4 py-8 relative overflow-hidden">
      {/* Decorative blobs */}
      <div className="absolute top-10 left-10 w-72 h-72 bg-olive/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-gold/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-olive to-olive/80 text-white flex items-center justify-center font-bold text-lg shadow-md mb-3">
            S
          </div>
          <div className="text-lg font-bold text-olive tracking-tight">Shichida India</div>
          <div className="text-[10px] text-text-muted uppercase tracking-widest">
            Early Learning Centres
          </div>
        </div>

        {/* Card */}
        <div className="card p-6">
          <h1 className="text-xl font-bold text-charcoal mb-6">{title}</h1>
          {children}
        </div>

        {/* Footer link */}
        <div className="mt-4 text-center text-sm text-text-muted">{footer}</div>
      </div>
    </div>
  );
}
