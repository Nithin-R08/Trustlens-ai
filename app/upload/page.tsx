"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Footer } from "../../components/Footer";
import { NavBar } from "../../components/NavBar";
import { analyzeDataset } from "../../lib/api";

const processingSteps = [
  "Reading dataset",
  "Profiling sensitive attributes",
  "Detecting class and group imbalance",
  "Computing fairness metrics",
  "Generating trust insights"
];

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isAnalyzing) {
      return;
    }
    const timer = window.setInterval(() => {
      setProgress((prev) => (prev >= 92 ? prev : prev + 4));
    }, 400);
    return () => {
      window.clearInterval(timer);
    };
  }, [isAnalyzing]);

  const currentStep = useMemo(() => {
    const stepIndex = Math.min(processingSteps.length - 1, Math.floor((progress / 100) * processingSteps.length));
    return processingSteps[stepIndex];
  }, [progress]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setErrorMessage(null);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setErrorMessage("Please choose a CSV or Excel file before starting analysis.");
      return;
    }

    try {
      setErrorMessage(null);
      setProgress(10);
      setIsAnalyzing(true);
      const result = await analyzeDataset(file);
      setProgress(100);
      router.push(`/results/${result.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to analyze dataset.";
      setErrorMessage(message);
      setIsAnalyzing(false);
      setProgress(0);
    }
  };

  return (
    <div className="min-h-screen bg-void text-white">
      <NavBar active="upload" />

      <main className="section-shell pt-28">
        <div className="mx-auto grid w-full max-w-6xl gap-8 lg:grid-cols-[1.2fr_1fr]">
          <section className="glass-card p-8">
            <p className="section-kicker">Dataset Upload</p>
            <h1 className="mt-4 font-headline text-4xl font-bold leading-tight text-white sm:text-5xl">
              Upload Data. Detect Bias. Build Trusted AI.
            </h1>
            <p className="mt-4 max-w-2xl text-slate-light/80">
              Upload your dataset dynamically. TrustLens will run fairness diagnostics before model training and generate
              explainable recommendations.
            </p>

            <form className="mt-8 space-y-6" onSubmit={onSubmit}>
              <label className="block">
                <span className="mb-3 block font-headline text-xs uppercase tracking-[0.16em] text-neon/80">
                  Dataset File
                </span>
                <input
                  type="file"
                  accept=".csv,.xls,.xlsx"
                  onChange={onFileChange}
                  className="block w-full rounded-xl border border-neon/20 bg-void-soft/80 px-4 py-4 text-sm text-slate-light file:mr-4 file:rounded-full file:border-0 file:bg-neon-strong file:px-4 file:py-2 file:font-headline file:text-xs file:font-bold file:uppercase file:tracking-[0.12em] file:text-[#002833] focus:border-neon/60 focus:outline-none"
                />
              </label>

              {file ? (
                <div className="rounded-xl border border-neon/15 bg-neon/5 p-4 text-sm text-slate-light/90">
                  <p>
                    Selected: <span className="text-white">{file.name}</span>
                  </p>
                  <p className="mt-1 text-xs text-slate-light/70">
                    Size: {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              ) : null}

              {errorMessage ? (
                <div className="rounded-xl border border-alert/35 bg-alert/10 px-4 py-3 text-sm text-alert">{errorMessage}</div>
              ) : null}

              <button type="submit" className="btn-primary w-full sm:w-auto" disabled={isAnalyzing}>
                {isAnalyzing ? "Analyzing..." : "Analyze Dataset"}
              </button>
            </form>
          </section>

          <aside className="space-y-6">
            <article className="glass-card p-6">
              <h2 className="font-headline text-lg font-bold text-neon">Supported Inputs</h2>
              <ul className="mt-4 space-y-2 text-sm text-slate-light/80">
                <li>CSV files (.csv)</li>
                <li>Excel files (.xls, .xlsx)</li>
                <li>No pre-upload dependency required</li>
              </ul>
            </article>

            <article className="glass-card p-6">
              <h2 className="font-headline text-lg font-bold text-neon">Output Includes</h2>
              <ul className="mt-4 space-y-2 text-sm text-slate-light/80">
                <li>Trust Score with risk level</li>
                <li>Fairness metric breakdown</li>
                <li>Proxy-bias indicators</li>
                <li>AI-generated insights and recommendations</li>
              </ul>
            </article>
          </aside>
        </div>
      </main>

      {isAnalyzing ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 px-4 backdrop-blur-md">
          <div className="w-full max-w-lg rounded-2xl border border-neon/30 bg-void/90 p-8">
            <p className="font-headline text-xs uppercase tracking-[0.2em] text-neon">TrustLens Processing</p>
            <h2 className="mt-3 font-headline text-2xl font-bold text-white">Analyzing Ethereal Intelligence</h2>
            <p className="mt-2 text-sm text-slate-light/80">{currentStep}</p>

            <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-neon-strong shadow-[0_0_16px_rgba(0,209,255,0.55)] transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-3 text-right font-headline text-xs uppercase tracking-[0.16em] text-neon">{progress}%</p>
          </div>
        </div>
      ) : null}

      <Footer />
    </div>
  );
}

