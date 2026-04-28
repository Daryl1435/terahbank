import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-navy flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 max-w-content mx-auto w-full">
        <div className="flex items-center gap-2">
          <img src="/logo-symbol.svg" alt="TerahBank" className="h-9" />
          <span className="font-poppins font-semibold text-xl text-white tracking-tight">
            TerahBank
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-mid-grey text-sm font-roboto">Mobile app available</span>
          <a
            href="http://localhost:8081"
            className="bg-teal text-white px-5 py-2.5 rounded-full font-poppins font-semibold text-sm hover:bg-teal-dark transition-colors"
          >
            Open app
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24">
        <div className="inline-flex items-center gap-2 bg-teal/10 border border-teal/30 rounded-full px-4 py-1.5 mb-8">
          <span className="w-2 h-2 rounded-full bg-teal animate-pulse" />
          <span className="text-teal text-sm font-roboto font-medium">Cameroon · Phase 1 Launch</span>
        </div>

        <h1 className="font-poppins font-bold text-5xl md:text-6xl text-white leading-tight max-w-3xl mb-6">
          Save. Grow.{' '}
          <span className="text-teal">Thrive.</span>
        </h1>

        <p className="text-mid-grey text-lg font-roboto max-w-xl mb-12 leading-relaxed">
          TerahBank is the first pan-African digital savings platform.
          Open an account in 5 minutes, deposit via MTN Mobile Money or Orange Money,
          and watch your money grow.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 items-center">
          <a
            href="http://localhost:8081"
            className="bg-teal text-white px-8 py-4 rounded-xl font-poppins font-semibold text-base hover:bg-teal-dark transition-colors shadow-lg shadow-teal/25"
          >
            Download the app →
          </a>
          <a
            href="http://localhost:8000/docs"
            className="text-mid-grey hover:text-white px-6 py-4 font-roboto text-base transition-colors"
          >
            API Documentation
          </a>
        </div>
      </section>

      {/* Feature grid */}
      <section className="max-w-content mx-auto w-full px-8 pb-24 grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          {
            icon: '🏦',
            title: 'Savings accounts',
            desc: 'Standard account, Project account with a goal, Term deposit at 2% p.a.',
          },
          {
            icon: '📱',
            title: 'Mobile Money',
            desc: 'Deposits and withdrawals via MTN Mobile Money and Orange Money in seconds.',
          },
          {
            icon: '🛡',
            title: 'Partner insurance',
            desc: 'Subscribe to health, device and micro-life insurance directly from the app.',
          },
        ].map((f) => (
          <div key={f.title} className="bg-dark-navy rounded-2xl p-6 border border-white/5">
            <span className="text-3xl mb-4 block">{f.icon}</span>
            <h3 className="font-poppins font-semibold text-white text-lg mb-2">{f.title}</h3>
            <p className="text-mid-grey font-roboto text-sm leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 px-8 text-center text-mid-grey text-sm font-roboto">
        © 2026 TerahBank · IBridge · CEMAC data residency · AWS af-south-1
        <span className="mx-3 opacity-30">|</span>
        <a href="http://localhost:3001" className="hover:text-teal transition-colors">
          Admin
        </a>
        <span className="mx-3 opacity-30">|</span>
        <a href="http://localhost:8000/docs" className="hover:text-teal transition-colors">
          API Docs
        </a>
      </footer>
    </main>
  );
}
