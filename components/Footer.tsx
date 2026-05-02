export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-void-soft/70 py-10">
      <div className="mx-auto flex w-full max-w-7xl flex-col items-center gap-5 px-4 text-center sm:px-8">
        <p className="font-headline text-lg font-bold uppercase tracking-[0.15em] text-neon">TrustLens AI</p>
        <p className="max-w-xl text-sm text-slate-light/75">
          We don&apos;t fix biased AI. We prevent biased AI before it is built.
        </p>
        <p className="text-xs uppercase tracking-[0.18em] text-slate-light/50">Safe and trusted AI starts with fair data.</p>
      </div>
    </footer>
  );
}

