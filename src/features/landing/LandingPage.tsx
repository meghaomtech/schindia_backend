import { useNavigate } from 'react-router-dom';

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#faf8f4] flex flex-col overflow-x-hidden">
      {/* Nav */}
      <header className="px-6 py-5 flex items-center justify-between max-w-6xl mx-auto w-full">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-olive to-olive/80 text-white flex items-center justify-center font-bold text-base shadow-md">
            S
          </div>
          <div>
            <div className="text-lg font-bold text-olive tracking-tight">Shichida India</div>
            <div className="text-[10px] text-text-muted uppercase tracking-widest">Early Learning Centres</div>
          </div>
        </div>
        <button
          onClick={() => navigate('/admin')}
          className="btn btn-primary shadow-md hover:shadow-lg transition-shadow"
        >
          Admin Portal →
        </button>
      </header>

      {/* Hero */}
      <main className="flex-1 flex items-center justify-center px-6 py-16 relative">
        {/* Decorative blobs */}
        <div className="absolute top-10 left-10 w-72 h-72 bg-olive/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-amber-100/40 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-olive/[0.03] rounded-full blur-2xl pointer-events-none" />

        <div className="max-w-3xl mx-auto text-center space-y-10 relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-olive/10 text-olive text-xs font-medium px-4 py-1.5 rounded-full">
            <span className="w-2 h-2 rounded-full bg-olive animate-pulse" />
            Trusted by 500+ families across India
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold text-charcoal leading-[1.1] tracking-tight">
            Nurturing Brilliance,<br />
            <span className="text-olive relative">
              One Child at a Time
              <svg className="absolute -bottom-2 left-0 w-full h-3 text-olive/20" viewBox="0 0 300 12" fill="none" preserveAspectRatio="none">
                <path d="M2 8c50-6 100-6 150-2s100 2 146-4" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
              </svg>
            </span>
          </h1>
          <p className="text-lg text-text-muted max-w-xl mx-auto leading-relaxed">
            Shichida India brings the renowned Shichida Method to early learners —
            developing memory, creativity, and confidence through joyful learning experiences.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap pt-2">
            <button
              onClick={() => navigate('/admin')}
              className="btn btn-primary px-8 py-3.5 text-base shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5"
            >
              Go to Admin Panel
            </button>
            <a
              href="#about"
              className="btn px-8 py-3.5 text-base border-2 border-olive/20 hover:border-olive/40 hover:bg-olive/5 transition-all"
            >
              Learn More ↓
            </a>
          </div>
        </div>
      </main>

      {/* Features */}
      <section id="about" className="max-w-5xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-charcoal">Everything you need to manage your centres</h2>
          <p className="text-text-muted mt-2">Powerful tools designed for early learning environments</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          <FeatureCard
            title="Multi-Centre Management"
            description="Manage multiple centres, rooms, sessions, and timetables from a single dashboard."
            icon="⚙️"
            accent="bg-amber-50 border-amber-100"
          />
          <FeatureCard
            title="Smart Scheduling"
            description="Visual timetable with automatic room and session conflict detection across all centres."
            icon="📊"
            accent="bg-emerald-50 border-emerald-100"
          />
          <FeatureCard
            title="Role-Based Access"
            description="Configure granular permissions for managers, teachers, and parents at each centre."
            icon="🔑"
            accent="bg-violet-50 border-violet-100"
          />
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-charcoal">The Shichida Method</h2>
          <p className="text-text-muted mt-2">A holistic approach to early childhood development</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-6">
          <MethodStep step="brain" title="Right Brain" desc="Stimulate imagination and intuition through speed play and flash cards" />
          <MethodStep step="memory" title="Memory" desc="Build photographic memory with linking and peg methods" />
          <MethodStep step="art" title="Music & Art" desc="Foster creativity through songs, art, and sensory activities" />
          <MethodStep step="bond" title="Love & Bond" desc="Strengthen parent-child connection as the foundation of learning" />
        </div>
      </section>

      {/* Testimonial */}
      <section className="max-w-3xl mx-auto px-6 py-20 text-center">
        <div className="text-4xl mb-6">💬</div>
        <blockquote className="text-xl text-charcoal italic leading-relaxed">
          "My daughter's memory and focus have improved remarkably in just 3 months.
          The Shichida method truly makes learning a joyful experience."
        </blockquote>
        <div className="mt-6 text-sm text-text-muted">
          <span className="font-medium text-charcoal">Priya Sharma</span> · Parent, Delhi Centre
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-6 pb-20">
        <div className="bg-gradient-to-br from-olive to-olive/90 rounded-2xl px-8 py-12 text-center text-white shadow-xl">
          <h3 className="text-2xl font-bold">Ready to get started?</h3>
          <p className="text-white/80 mt-2 max-w-md mx-auto">
            Access your centre's admin panel to manage sessions, children, and schedules.
          </p>
          <button
            onClick={() => navigate('/admin')}
            className="mt-6 bg-white text-olive font-semibold px-8 py-3 rounded-lg shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all"
          >
            Open Admin Panel →
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-8 border-t border-border bg-white/50">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-olive text-white flex items-center justify-center font-bold text-xs">
              S
            </div>
            <span className="text-sm font-medium text-charcoal">Shichida India</span>
          </div>
          <div className="text-sm text-text-muted">
            © 2026 Shichida India. All rights reserved.
          </div>
          <div className="text-xs text-text-dim">
            Admin Portal v0.1
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ title, description, icon, accent }: { title: string; description: string; icon: string; accent: string }) {
  return (
    <div className={`rounded-xl border p-7 text-center space-y-4 hover:shadow-lg transition-all hover:-translate-y-1 ${accent}`}>
      <div className="w-12 h-12 mx-auto rounded-xl bg-olive/10 flex items-center justify-center">
        {icon === '⚙️' && (
          <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-olive">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
          </svg>
        )}
        {icon === '📊' && (
          <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-olive">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z" />
          </svg>
        )}
        {icon === '🔑' && (
          <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-olive">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
          </svg>
        )}
      </div>
      <div className="font-semibold text-charcoal text-lg">{title}</div>
      <div className="text-sm text-text-muted leading-relaxed">{description}</div>
    </div>
  );
}

function MethodStep({ step, title, desc }: { step: string; title: string; desc: string }) {
  return (
    <div className="text-center space-y-3">
      <div className="w-12 h-12 rounded-full bg-olive/10 flex items-center justify-center mx-auto">
        {step === 'brain' && (
          <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-olive">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
          </svg>
        )}
        {step === 'memory' && (
          <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-olive">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z" />
          </svg>
        )}
        {step === 'art' && (
          <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-olive">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42" />
          </svg>
        )}
        {step === 'bond' && (
          <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="text-olive">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
          </svg>
        )}
      </div>
      <div className="font-semibold text-charcoal">{title}</div>
      <div className="text-xs text-text-muted leading-relaxed">{desc}</div>
    </div>
  );
}

