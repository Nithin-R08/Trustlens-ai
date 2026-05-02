"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Footer } from "../../../components/Footer";
import { NavBar } from "../../../components/NavBar";
import { fetchResultById, getReportUrl, isApiConfigured, type TrustLensResult } from "../../../lib/api";

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric-tile">
      <p className="metric-label">{label}</p>
      <p className="mt-2 font-headline text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

export default function ResultDetailsPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";

  const [result, setResult] = useState<TrustLensResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id || id === "latest") {
      setLoading(false);
      return;
    }

    let isMounted = true;
    fetchResultById(id)
      .then((payload) => {
        if (!isMounted) {
          return;
        }
        setResult(payload);
        setErrorMessage(null);
      })
      .catch((error) => {
        if (!isMounted) {
          return;
        }
        const message = error instanceof Error ? error.message : "Unable to load result.";
        setErrorMessage(message);
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [id]);

  const gauge = useMemo(() => {
    const score = result?.trust_score ?? 0;
    return {
      score,
      style: {
        background: `conic-gradient(#00d1ff ${Math.max(0, Math.min(100, score)) * 3.6}deg, rgba(255,255,255,0.12) 0deg)`
      }
    };
  }, [result]);

  const jsonReportUrl = result ? getReportUrl(result.id, "json") : "";
  const pdfReportUrl = result && isApiConfigured() ? getReportUrl(result.id, "pdf") : "";

  return (
    <div className="min-h-screen bg-void text-white">
      <NavBar active="results" />

      <main className="section-shell pt-28">
        <div className="mx-auto w-full max-w-7xl">
          {id === "latest" ? (
            <section className="glass-card p-10 text-center">
              <h1 className="font-headline text-3xl font-bold text-white">No latest result selected yet</h1>
              <p className="mt-3 text-slate-light/80">
                Upload and analyze a dataset to generate your first trust report.
              </p>
              <Link href="/upload" className="btn-primary mt-8">
                Go to Upload
              </Link>
            </section>
          ) : null}

          {loading ? (
            <section className="glass-card p-10">
              <p className="section-kicker">Loading Result</p>
              <h1 className="mt-3 font-headline text-3xl font-bold">Computing visual report...</h1>
            </section>
          ) : null}

          {!loading && errorMessage ? (
            <section className="rounded-2xl border border-alert/40 bg-alert/10 p-6 text-alert">{errorMessage}</section>
          ) : null}

          {!loading && result ? (
            <section className="space-y-8">
              <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
                <article className="glass-card p-8">
                  <p className="section-kicker">Trust Score</p>
                  <div className="mt-6 flex flex-col items-center gap-5 text-center sm:flex-row sm:text-left">
                    <div className="relative grid h-40 w-40 place-items-center rounded-full p-[10px]" style={gauge.style}>
                      <div className="grid h-full w-full place-items-center rounded-full bg-void">
                        <p className="font-headline text-4xl font-bold text-white">{gauge.score}</p>
                      </div>
                    </div>
                    <div>
                      <h1 className="font-headline text-3xl font-bold text-white sm:text-4xl">{result.bias_risk} Risk</h1>
                      <p className="mt-2 text-sm text-slate-light/80">Dataset: {result.dataset_name}</p>
                      <p className="mt-2 text-sm text-slate-light/80">
                        Sensitive Attributes:{" "}
                        {result.sensitive_attributes.length ? result.sensitive_attributes.join(", ") : "Not detected"}
                      </p>
                    </div>
                  </div>
                </article>

                <article className="glass-card p-8">
                  <p className="section-kicker">Report</p>
                  <h2 className="mt-3 font-headline text-2xl font-bold">Download Output</h2>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <a href={jsonReportUrl} className="btn-secondary" target="_blank" rel="noreferrer">
                      JSON Report
                    </a>
                    {pdfReportUrl ? (
                      <a href={pdfReportUrl} className="btn-primary" target="_blank" rel="noreferrer">
                        PDF Report
                      </a>
                    ) : null}
                  </div>
                </article>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <MetricCard label="Demographic Parity Difference" value={result.metrics.demographic_parity_difference} />
                <MetricCard label="Disparate Impact Ratio" value={result.metrics.disparate_impact_ratio} />
                <MetricCard label="Statistical Parity" value={result.metrics.statistical_parity} />
                <MetricCard
                  label="Representation Imbalance"
                  value={result.metrics.representation_imbalance_score}
                />
                <MetricCard label="Class Balance Ratio" value={result.metrics.class_balance_ratio ?? "-"} />
                <MetricCard label="Proxy Feature Count" value={result.metrics.proxy_feature_count ?? "-"} />
              </div>

              <article className="glass-card p-8">
                <p className="section-kicker">Explainability</p>
                <h2 className="mt-3 font-headline text-2xl font-bold">AI Insights</h2>
                <p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-slate-light/85">{result.insights}</p>
              </article>

              <article className="glass-card p-8">
                <p className="section-kicker">Recommendation Engine</p>
                <h2 className="mt-3 font-headline text-2xl font-bold">Mitigation Actions</h2>
                <ul className="mt-4 space-y-3 text-sm text-slate-light/85">
                  {result.recommendations.map((recommendation) => (
                    <li key={recommendation} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                      {recommendation}
                    </li>
                  ))}
                </ul>
              </article>
            </section>
          ) : null}
        </div>
      </main>

      <Footer />
    </div>
  );
}
