import Link from "next/link";
import { Footer } from "../components/Footer";
import { NavBar } from "../components/NavBar";
import SplineHero from "../components/SplineHero";

const features = [
  {
    title: "Bias Detection Engine",
    description:
      "Runs distribution analysis, class imbalance checks, and group-level comparisons before model training."
  },
  {
    title: "Fairness Metrics",
    description:
      "Computes demographic parity difference, disparate impact ratio, statistical parity, and representation imbalance."
  },
  {
    title: "Trust Score System",
    description:
      "Combines fairness, representation, and proxy-bias signals into a transparent 0-100 trust score."
  }
];

const steps = [
  { title: "Upload Dataset", detail: "Upload CSV or Excel directly from your workspace." },
  { title: "Analyze Bias", detail: "TrustLens profiles sensitive attributes and checks for proxy bias." },
  { title: "Generate Trust Score", detail: "Metrics are converted into a risk-aware trust score." },
  { title: "Get Action Plan", detail: "Receive explainable insights and concrete mitigation recommendations." }
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-void text-white">
      <NavBar active="home" />
      <main>
        <SplineHero />

        <section className="section-shell">
          <div className="mx-auto max-w-7xl">
            <div className="mb-10 text-center">
              <p className="section-kicker">Core Capabilities</p>
              <h2 className="section-title">Advanced Fairness Frameworks</h2>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
              {features.map((feature) => (
                <article key={feature.title} className="glass-card p-7">
                  <h3 className="font-headline text-xl font-bold text-neon">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-light/85">{feature.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section-shell bg-void-soft/60">
          <div className="mx-auto max-w-7xl">
            <div className="grid gap-6 md:grid-cols-4">
              {steps.map((step, index) => (
                <article key={step.title} className="glass-card p-6">
                  <p className="font-headline text-4xl font-bold text-white/20">0{index + 1}</p>
                  <h3 className="mt-3 font-headline text-lg font-semibold text-neon">{step.title}</h3>
                  <p className="mt-2 text-sm text-slate-light/80">{step.detail}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section-shell">
          <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-2">
            <div>
              <p className="section-kicker">Live Dashboard</p>
              <h2 className="section-title !text-left">
                Bias Signals, Fairness Metrics, and Trust in a Single View
              </h2>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-light/80">
                TrustLens AI is built for teams that want fairness checks before training begins. Upload a dataset,
                inspect sensitive group coverage, detect proxy features, and generate a trust-ready report instantly.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link href="/upload" className="btn-primary">
                  Start Analysis
                </Link>
                <Link href="/results/latest" className="btn-secondary">
                  View Sample Results
                </Link>
              </div>
            </div>

            <div className="glass-card p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="metric-tile">
                  <p className="metric-label">Bias Risk</p>
                  <p className="metric-value text-alert">Medium</p>
                </div>
                <div className="metric-tile">
                  <p className="metric-label">Trust Score</p>
                  <p className="metric-value text-neon">72/100</p>
                </div>
                <div className="metric-tile sm:col-span-2">
                  <p className="metric-label">Pipeline Steps</p>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-light/70">
                    <span>Data Ingestion</span>
                    <span>Bias Detection</span>
                    <span>Fairness Metrics</span>
                    <span>Recommendations</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
