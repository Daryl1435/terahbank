export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col overflow-x-hidden">

      {/* ── Nav ─────────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-white border-b border-light-grey">
        <div className="max-w-content mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2.5 shrink-0">
            <img src="/logo-symbol.svg" alt="TerahBank" className="h-8 w-8" />
            <span className="font-poppins font-bold text-lg text-navy tracking-tight">TerahBank</span>
          </a>

          <div className="hidden md:flex items-center gap-7">
            {['Personal', 'Business', 'Security'].map((item) => (
              <a key={item} href="#" className="text-dark-grey hover:text-navy text-sm font-roboto transition-colors">
                {item}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <a href="http://localhost:8081" className="hidden sm:block text-dark-grey hover:text-navy text-sm font-roboto transition-colors">
              Log in
            </a>
            <a
              href="http://localhost:8081"
              className="bg-teal text-white px-5 py-2.5 rounded-full font-poppins font-semibold text-sm hover:bg-teal-dark transition-colors"
            >
              Open account
            </a>
          </div>
        </div>
      </nav>

      {/* ── Hero — full-viewport, light, split layout ───────────────────────── */}
      <section className="bg-off-white overflow-hidden">
        <div className="max-w-content mx-auto px-6 md:px-10 w-full grid grid-cols-1 md:grid-cols-2 gap-10 items-end">

          {/* Left: text */}
          <div className="pt-20 pb-16 md:pb-24">
            <h1 className="font-poppins font-black text-5xl md:text-6xl text-navy leading-[1.0] mb-5 tracking-tight">
              SAVE MONEY<br />
              IN CAMEROON<br />
              FOR FREE
            </h1>
            <p className="text-dark-grey font-roboto text-base md:text-lg leading-relaxed mb-8 max-w-md">
              Open a savings account in 5 minutes. Deposit instantly via MTN MoMo or Orange Money.
              Earn 2% p.a. with zero account fees — every time.
            </p>
            <a
              href="http://localhost:8081"
              className="inline-block bg-teal text-white px-8 py-3.5 rounded-full font-poppins font-semibold text-base hover:bg-teal-dark transition-colors"
            >
              Open an account
            </a>
          </div>

          {/* Right: realistic app mockup */}
          <div className="flex justify-center md:justify-end pt-10 md:pt-0">
            <div className="relative w-72 translate-y-6">

              {/* Phone */}
              <div className="relative bg-dark-navy border border-white/10 rounded-3xl overflow-hidden shadow-2xl shadow-navy/30">
                {/* Status bar */}
                <div className="px-5 pt-4 pb-3 flex items-center justify-between">
                  <span className="text-white/50 text-xs font-roboto">9:41</span>
                  <div className="flex items-center gap-1.5">
                    <svg className="w-3 h-3 text-white/50" fill="currentColor" viewBox="0 0 16 12" aria-hidden="true">
                      <rect x="0" y="3" width="2" height="9" rx="1" /><rect x="4" y="2" width="2" height="10" rx="1" /><rect x="8" y="0" width="2" height="12" rx="1" /><rect x="12" y="0" width="2" height="12" rx="1" />
                    </svg>
                    <svg className="w-5 h-3 text-white/50" fill="currentColor" viewBox="0 0 22 12" aria-hidden="true">
                      <rect x="0" y="1" width="18" height="10" rx="2" stroke="currentColor" strokeWidth="1.2" fill="none" /><rect x="1.5" y="2.5" width="8" height="7" rx="1" fill="currentColor" /><path d="M19.5 4v4a2 2 0 000-4z" fill="currentColor" />
                    </svg>
                  </div>
                </div>

                <div className="px-5 pb-7">
                  {/* App header */}
                  <div className="flex items-center justify-between mb-5">
                    <div>
                      <p className="text-white/40 text-xs font-roboto">Good morning,</p>
                      <p className="text-white font-poppins font-semibold text-sm">Daryl 👋</p>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-teal/20 flex items-center justify-center">
                      <svg className="w-4 h-4 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                      </svg>
                    </div>
                  </div>

                  {/* Balance */}
                  <div className="bg-navy/50 border border-white/10 rounded-2xl p-4 mb-4">
                    <p className="text-white/40 text-xs font-roboto uppercase tracking-wider mb-1">Total balance</p>
                    <p className="text-white font-poppins font-bold text-3xl tracking-tight">
                      1,250,000 <span className="text-teal font-semibold text-lg">XAF</span>
                    </p>
                    <div className="flex items-center gap-1.5 mt-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-success" />
                      <span className="text-success text-xs font-roboto">+2,500 XAF this month</span>
                    </div>
                  </div>

                  {/* Quick actions */}
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    {[
                      { label: 'Deposit', d: 'M19 14l-7 7m0 0l-7-7m7 7V3' },
                      { label: 'Withdraw', d: 'M5 10l7-7m0 0l7 7m-7-7v18' },
                      { label: 'Transfer', d: 'M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4' },
                    ].map((action) => (
                      <div key={action.label} className="bg-white/[6%] border border-white/[6%] rounded-xl py-3 flex flex-col items-center gap-1.5">
                        <svg className="w-4 h-4 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d={action.d} />
                        </svg>
                        <span className="text-white/70 text-xs font-roboto">{action.label}</span>
                      </div>
                    ))}
                  </div>

                  {/* Transactions */}
                  <div>
                    <p className="text-white/30 text-xs font-roboto uppercase tracking-wider mb-3">Recent</p>
                    <div className="space-y-3">
                      {[
                        { name: 'MTN MoMo deposit', sub: 'Today, 09:14', amount: '+50,000', positive: true },
                        { name: 'Term deposit', sub: 'Yesterday', amount: '-500,000', positive: false },
                        { name: 'Interest credited', sub: 'Jun 1', amount: '+2,500', positive: true },
                      ].map((tx) => (
                        <div key={tx.name} className="flex items-center justify-between">
                          <div>
                            <p className="text-white/80 text-xs font-roboto font-medium">{tx.name}</p>
                            <p className="text-white/30 text-xs font-roboto">{tx.sub}</p>
                          </div>
                          <span className={`text-xs font-roboto font-semibold ${tx.positive ? 'text-success' : 'text-warning'}`}>
                            {tx.amount}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating stat badge */}
              <div className="absolute -right-12 top-16 bg-white rounded-2xl shadow-xl px-4 py-3 flex items-center gap-3 border border-light-grey">
                <div className="w-9 h-9 rounded-xl bg-teal/10 flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div>
                  <p className="font-poppins font-bold text-navy text-sm leading-none">2% p.a.</p>
                  <p className="font-roboto text-dark-grey text-xs mt-0.5">Annual return</p>
                </div>
              </div>

            </div>
          </div>
        </div>
      </section>

      {/* ── Trust strip ─────────────────────────────────────────────────────── */}
      <section className="bg-white border-y border-light-grey py-10">
        <div className="max-w-content mx-auto px-6 md:px-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:divide-x divide-light-grey">
            {[
              {
                icon: <svg className="w-5 h-5 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
                title: 'Trusted by thousands in Cameroon',
                desc: '10,000+ early users growing their savings with TerahBank',
              },
              {
                icon: <svg className="w-5 h-5 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
                title: 'CEMAC licensed and regulated',
                desc: 'Fully compliant with Central African banking regulations',
              },
              {
                icon: <svg className="w-5 h-5 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" /></svg>,
                title: '24/7 customer support',
                desc: 'Help via in-app chat, phone, or email — any time, any day',
              },
            ].map((item) => (
              <div key={item.title} className="flex items-start gap-4 px-0 md:px-8 first:pl-0 last:pr-0">
                <div className="w-10 h-10 bg-teal/[8%] rounded-xl flex items-center justify-center shrink-0">
                  {item.icon}
                </div>
                <div>
                  <p className="font-poppins font-semibold text-navy text-sm mb-1">{item.title}</p>
                  <p className="font-roboto text-dark-grey text-sm leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── No hidden fees ───────────────────────────────────────────────────── */}
      <section className="bg-navy py-24 px-6">
        <div className="max-w-content mx-auto grid grid-cols-1 md:grid-cols-2 gap-16 items-start">
          <div>
            <h2 className="font-poppins font-black text-4xl md:text-5xl text-white leading-[1.0] mb-5">
              NEVER PAY A<br />HIDDEN FEE AGAIN
            </h2>
            <p className="text-mid-grey font-roboto text-base leading-relaxed mb-8">
              Other banks hide fees in the fine print. We don't. Everything at TerahBank is transparent
              — see for yourself.
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <a href="http://localhost:8081" className="inline-block bg-teal text-white px-7 py-3.5 rounded-full font-poppins font-semibold text-sm hover:bg-teal-dark transition-colors">
                Save money now
              </a>
              <a href="#" className="inline-block text-white/60 hover:text-white border border-white/15 hover:border-white/30 px-7 py-3.5 rounded-full font-roboto text-sm transition-colors text-center">
                Learn how it works
              </a>
            </div>
          </div>

          <div className="bg-white/[4%] border border-white/10 rounded-2xl overflow-hidden">
            <div className="grid grid-cols-3 bg-white/[4%] px-6 py-4 border-b border-white/10">
              <span className="text-mid-grey text-sm font-roboto font-medium">Fee type</span>
              <span className="text-teal text-sm font-poppins font-semibold text-center">TerahBank</span>
              <span className="text-mid-grey text-sm font-roboto text-center">Others</span>
            </div>
            {[
              { type: 'Account opening', us: 'Free', them: '5,000 – 15,000 XAF' },
              { type: 'Monthly fee', us: 'Free', them: '1,000 – 3,000 XAF' },
              { type: 'MoMo deposit', us: 'Free', them: '0.5% – 1%' },
              { type: 'Minimum balance', us: 'None', them: '25,000 – 50,000 XAF' },
              { type: 'Interest on savings', us: '2% p.a.', them: '0% – 0.5%' },
            ].map((row) => (
              <div key={row.type} className="grid grid-cols-3 px-6 py-4 border-b border-white/[5%] last:border-0">
                <span className="text-mid-grey text-sm font-roboto">{row.type}</span>
                <span className="text-teal text-sm font-poppins font-semibold text-center">{row.us}</span>
                <span className="text-white/25 text-sm font-roboto text-center line-through">{row.them}</span>
              </div>
            ))}
          </div>
        </div>
        <p className="max-w-content mx-auto mt-4 text-white/20 text-xs font-roboto">
          * Comparison based on major Cameroonian commercial banks, May 2026.
        </p>
      </section>

      {/* ── Features ─────────────────────────────────────────────────────────── */}
      <section className="bg-off-white py-24 px-6">
        <div className="max-w-content mx-auto">
          <div className="max-w-xl mb-14">
            <p className="text-teal text-xs font-roboto font-semibold uppercase tracking-widest mb-4">What we offer</p>
            <h2 className="font-poppins font-black text-4xl md:text-5xl text-navy leading-[1.0]">
              EVERYTHING YOU<br />NEED TO THRIVE
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {[
              {
                tag: 'Savings',
                title: 'Three account types',
                desc: 'Standard, Project (goal-based), and Term Deposit at 2% p.a. — all in one app.',
                icon: <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>,
              },
              {
                tag: 'Payments',
                title: 'MTN MoMo & Orange Money',
                desc: 'Instant deposits and withdrawals from your mobile wallet — no bank visit needed.',
                icon: <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden="true"><rect x="5" y="2" width="14" height="20" rx="2" strokeLinecap="round" strokeLinejoin="round" /><path strokeLinecap="round" strokeLinejoin="round" d="M12 18h.01M8.5 7.5a5 5 0 017 0M10.5 10a2 2 0 013 0" /></svg>,
              },
              {
                tag: 'Protection',
                title: 'Partner insurance',
                desc: 'Health, device, and micro-life insurance from trusted partners, right from the app.',
                icon: <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
              },
            ].map((item) => (
              <div key={item.title} className="group bg-white border border-light-grey hover:border-teal/30 rounded-2xl p-7 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
                <div className="flex items-center justify-between mb-6">
                  <span className="bg-teal/10 text-teal text-xs font-roboto font-semibold px-3 py-1 rounded-full">{item.tag}</span>
                  <div className="text-teal group-hover:scale-110 transition-transform duration-300">{item.icon}</div>
                </div>
                <h3 className="font-poppins font-semibold text-navy text-lg mb-3">{item.title}</h3>
                <p className="font-roboto text-dark-grey text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security ─────────────────────────────────────────────────────────── */}
      <section className="bg-white py-24 px-6 border-t border-light-grey">
        <div className="max-w-content mx-auto grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
          <div>
            <h2 className="font-poppins font-black text-4xl md:text-5xl text-navy leading-tight mb-5">
              BUILT TO KEEP<br />YOUR MONEY SAFE
            </h2>
            <p className="text-dark-grey font-roboto text-base leading-relaxed mb-10">
              Every month, customers trust us with their savings. We take that seriously —
              with the same security standards used by global banks.
            </p>
            <a href="#" className="inline-block border border-navy/25 text-navy hover:bg-navy hover:text-white px-7 py-3.5 rounded-full font-roboto text-sm transition-all duration-200">
              How we keep your money safe →
            </a>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {[
              { title: '256-bit TLS', desc: 'All data encrypted in transit and at rest.', icon: <svg className="w-5 h-5 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path strokeLinecap="round" d="M7 11V7a5 5 0 0110 0v4" /></svg> },
              { title: '2-factor auth', desc: 'OTP on every login and transaction.', icon: <svg className="w-5 h-5 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg> },
              { title: 'CEMAC regulated', desc: 'Licensed under Central African banking law.', icon: <svg className="w-5 h-5 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M3 21h18M3 10h18M3 7l9-4 9 4M4 10h1v11H4zm6 0h1v11h-1zm5 0h1v11h-1zm5 0h1v11h-1z" /></svg> },
              { title: 'AWS Cape Town', desc: 'Data stored in Africa — CEMAC compliant.', icon: <svg className="w-5 h-5 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" /></svg> },
            ].map((item) => (
              <div key={item.title} className="bg-off-white rounded-2xl p-5 border border-light-grey">
                <div className="w-10 h-10 bg-teal/[8%] rounded-xl flex items-center justify-center mb-4">{item.icon}</div>
                <h3 className="font-poppins font-semibold text-navy text-sm mb-2">{item.title}</h3>
                <p className="font-roboto text-dark-grey text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ─────────────────────────────────────────────────────── */}
      <section className="bg-off-white py-20 px-6 border-t border-light-grey">
        <div className="max-w-content mx-auto">
          <h2 className="font-poppins font-black text-4xl md:text-5xl text-navy leading-tight mb-12">
            FOR PEOPLE<br />GROWING IN AFRICA
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {[
              { flag: '🇨🇲', location: 'Yaoundé', name: 'Marie N.', quote: '"I opened my account in under 4 minutes. My MTN MoMo deposit landed instantly. This is what banking in Cameroon should have been years ago."' },
              { flag: '🇨🇲', location: 'Douala', name: 'Paul K.', quote: '"My term deposit earns 2% a year — I checked three banks before and none came close. TerahBank completely changed how I save."' },
              { flag: '🇨🇲', location: 'Bafoussam', name: 'Aissatou B.', quote: '"The project savings account let me set a goal for my daughter\'s school fees. Watching the progress bar fill up kept me motivated every week."' },
            ].map((t) => (
              <div key={t.name} className="bg-dark-navy rounded-2xl p-7 flex flex-col">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-10 h-10 rounded-full bg-teal/15 flex items-center justify-center text-xl shrink-0">{t.flag}</div>
                  <div>
                    <p className="font-poppins font-semibold text-white text-sm">{t.name}</p>
                    <p className="font-roboto text-mid-grey text-xs">{t.location}</p>
                  </div>
                </div>
                <p className="text-white/70 font-roboto text-sm leading-relaxed">{t.quote}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Mission CTA ──────────────────────────────────────────────────────── */}
      <section className="bg-dark-navy py-28 px-6">
        <div className="max-w-content mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          <h2 className="font-poppins font-black text-5xl md:text-7xl text-white leading-[0.95] tracking-tight">
            BANKING<br />FOR AFRICA,<br />
            <span className="gradient-text">BUILT IN<br />AFRICA</span>
          </h2>
          <div>
            <p className="text-mid-grey font-roboto text-lg leading-relaxed mb-4">
              We're building the most accessible savings platform for Central Africa.
              No hidden fees. Real returns. Technology that works on any connection.
            </p>
            <p className="text-mid-grey font-roboto text-base leading-relaxed mb-10 italic">Min fees. Max ease. Full speed.</p>
            <a href="#" className="inline-block border border-white/20 text-white hover:bg-white hover:text-navy px-8 py-4 rounded-full font-poppins font-semibold text-base transition-all duration-200">
              Learn about our mission →
            </a>
          </div>
        </div>
      </section>

      {/* ── App download ─────────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-br from-teal/20 via-teal/10 to-off-white py-16 px-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-3xl p-10 md:p-14 text-center shadow-xl border border-light-grey">
            <h2 className="font-poppins font-black text-3xl md:text-4xl text-navy leading-tight mb-3">
              GET THE APP FOR<br />MANAGING MONEY<br />EVERYWHERE
            </h2>
            <p className="text-dark-grey font-roboto text-base mb-8">Available for Android · iOS coming soon</p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <a href="http://localhost:8081" className="flex items-center justify-center gap-3 bg-navy text-white px-7 py-3.5 rounded-xl font-poppins font-semibold text-sm hover:bg-dark-navy transition-colors">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.523 15.341l1.5 2.598a.75.75 0 01-1.299.752l-1.5-2.598A6.704 6.704 0 0112 17a6.704 6.704 0 01-4.224-1.907l-1.5 2.598a.75.75 0 01-1.299-.752l1.5-2.598A6.75 6.75 0 015.25 9.75v-.75H3.75a.75.75 0 010-1.5h.56L5.842 4.5A1.5 1.5 0 017.32 3.75h9.36a1.5 1.5 0 011.479 1.073L19.69 7.5h.56a.75.75 0 010 1.5h-1.5v.75a6.75 6.75 0 01-1.227 3.841zM9 2.25a.75.75 0 000 1.5h6a.75.75 0 000-1.5H9zm3 9a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/></svg>
                Get it on Android
              </a>
              <span className="flex items-center justify-center gap-3 border border-light-grey text-mid-grey px-7 py-3.5 rounded-xl font-roboto text-sm cursor-not-allowed select-none">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
                iOS — Coming Soon
              </span>
            </div>
            <p className="text-mid-grey font-roboto text-xs mt-6">No credit card required · Free to open</p>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer className="bg-dark-navy border-t border-white/5">
        <div className="max-w-content mx-auto px-6 md:px-10 pt-16 pb-10 grid grid-cols-2 md:grid-cols-4 gap-10">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <img src="/logo-symbol.svg" alt="TerahBank" className="h-8 w-8" />
              <span className="font-poppins font-bold text-base text-white">TerahBank</span>
            </div>
            <p className="font-roboto text-mid-grey text-sm leading-relaxed max-w-[180px]">Pan-African digital savings. Built by IBridge for Cameroon.</p>
          </div>
          {[
            { title: 'Products', links: ['Savings accounts', 'Mobile Money', 'Insurance', 'API'] },
            { title: 'Company', links: ['About', 'Careers', 'Blog', 'Press'] },
            { title: 'Legal', links: ['Privacy', 'Terms', 'Compliance', 'Security'] },
          ].map((col) => (
            <div key={col.title}>
              <p className="font-poppins font-semibold text-white text-sm mb-5">{col.title}</p>
              <ul className="space-y-3.5">
                {col.links.map((link) => (
                  <li key={link}><a href="#" className="font-roboto text-mid-grey text-sm hover:text-white transition-colors">{link}</a></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-white/5 py-6 px-6 md:px-10">
          <div className="max-w-content mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-mid-grey text-xs font-roboto">
            <span>© 2026 TerahBank · IBridge · CEMAC data residency · AWS af-south-1</span>
            <div className="flex items-center gap-5">
              <a href="http://localhost:3001" className="hover:text-teal transition-colors">Admin</a>
              <a href="http://localhost:8000/docs" className="hover:text-teal transition-colors">API Docs</a>
            </div>
          </div>
        </div>
      </footer>

    </main>
  );
}
