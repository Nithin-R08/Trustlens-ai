"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Component, useCallback, useEffect, useRef, useState } from "react";

const SplineScene = dynamic(
  () => import("@splinetool/react-spline").then((module) => module.default),
  { ssr: false, loading: () => <div className="h-full w-full bg-void" /> }
);

const SPLINE_EMBED_URL = "https://my.spline.design/unchained-WgbTDe9RnAlSWiXPchrvW3eg/";
const SPLINE_SCENE_URL = "https://prod.spline.design/WgbTDe9RnAlSWiXPchrvW3eg/scene.splinecode";
const ENABLE_SPLINE_RUNTIME = process.env.NEXT_PUBLIC_ENABLE_SPLINE_RUNTIME === "1";

class SplineRuntimeBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch() {
    if (typeof this.props.onRuntimeError === "function") {
      this.props.onRuntimeError();
    }
  }

  render() {
    if (this.state.hasError) {
      return <div className="h-full w-full bg-void" />;
    }
    return this.props.children;
  }
}

export default function SplineHero() {
  const [useIframeFallback, setUseIframeFallback] = useState(true);
  const scrollOverlayRef = useRef(null);
  const reEnableTimer = useRef(null);

  /* ── Scroll-capture overlay logic ──
   * The overlay sits on top of the Spline iframe (z-[5]) with pointer-events: auto.
   * - wheel events  → intercepted and forwarded as page scroll
   * - mousemove     → overlay briefly disables its own pointer-events
   *                   so subsequent mouse events reach the Spline iframe
   *                   underneath, enabling Spline's native 3D rotation.
   *                   After 150ms of no mouse movement, pointer-events
   *                   are re-enabled to capture the next wheel event.
   */

  useEffect(() => {
    const overlay = scrollOverlayRef.current;
    if (!overlay) return;

    const handleWheel = (e) => {
      e.preventDefault();
      e.stopPropagation();
      window.scrollBy({ top: e.deltaY, left: e.deltaX, behavior: "instant" });
    };

    overlay.addEventListener("wheel", handleWheel, { passive: false });
    return () => overlay.removeEventListener("wheel", handleWheel);
  }, []);

  const handleOverlayMouseMove = useCallback(() => {
    const overlay = scrollOverlayRef.current;
    if (!overlay) return;

    // Disable overlay so mouse events pass through to Spline iframe
    overlay.style.pointerEvents = "none";

    // Re-enable after mouse stops moving so we can catch next wheel event
    clearTimeout(reEnableTimer.current);
    reEnableTimer.current = setTimeout(() => {
      if (scrollOverlayRef.current) {
        scrollOverlayRef.current.style.pointerEvents = "auto";
      }
    }, 150);
  }, []);

  const handleSplineLoad = (splineApp) => {
    try {
      if (typeof splineApp?.setZoom === "function") {
        splineApp.setZoom(1.35);
      }
    } catch {
      // Ignore camera adjustment errors and continue rendering.
    }
  };

  const handleSplineFailure = () => {
    setUseIframeFallback(true);
  };

  useEffect(() => {
    if (!ENABLE_SPLINE_RUNTIME) {
      return;
    }

    const handleUnhandledRejection = (event) => {
      const reasonText =
        event.reason instanceof Error
          ? event.reason.message
          : typeof event.reason === "string"
          ? event.reason
          : String(event.reason ?? "");

      if (reasonText.toLowerCase().includes("failed to fetch")) {
        event.preventDefault();
        setUseIframeFallback(true);
      }
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);
    return () => {
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);

  useEffect(() => {
    return () => clearTimeout(reEnableTimer.current);
  }, []);

  return (
    <header className="relative h-[100vh] min-h-[100vh] w-full overflow-hidden">
      <div className="trustlens-hero-fallback absolute inset-0 z-0" aria-hidden="true">
        <div className="trustlens-grid" />
        <div className="trustlens-core">
          <span className="trustlens-ring trustlens-ring-a" />
          <span className="trustlens-ring trustlens-ring-b" />
          <span className="trustlens-ring trustlens-ring-c" />
          <span className="trustlens-prism" />
          <span className="trustlens-scanline" />
        </div>
      </div>

      {/* Spline scene – z-0, receives mouse events when overlay is disabled */}
      <div className="absolute inset-0 z-[1] h-full w-full overflow-hidden opacity-90 mix-blend-screen">
        <div className="absolute inset-0 scale-[1.08] sm:scale-[1.03]">
          {useIframeFallback ? (
            <iframe
              src={SPLINE_EMBED_URL}
              title="TrustLens AI Spline Scene"
              className="h-full w-full border-0"
              style={{ display: "block" }}
              loading="eager"
              allowFullScreen
            />
          ) : (
            <SplineRuntimeBoundary onRuntimeError={handleSplineFailure}>
              <SplineScene
                scene={SPLINE_SCENE_URL}
                onLoad={handleSplineLoad}
                onError={handleSplineFailure}
                style={{ width: "100%", height: "100%" }}
              />
            </SplineRuntimeBoundary>
          )}
        </div>
      </div>

      {/* Scroll-forwarding overlay – captures wheel, passes mousemove through */}
      <div
        ref={scrollOverlayRef}
        onMouseMove={handleOverlayMouseMove}
        className="absolute inset-0 z-[5]"
        style={{ pointerEvents: "auto", background: "transparent" }}
      />

      {/* Dark tint */}
      <div
        className="absolute inset-0 z-10 bg-black/15"
        style={{ pointerEvents: "none" }}
      />

      {/* Text content */}
      <div
        className="relative z-20 mx-auto flex h-full w-full max-w-7xl flex-col items-center justify-center px-4 pb-12 pt-24 text-center sm:px-8 sm:pt-28"
        style={{ pointerEvents: "none" }}
      >
        <p className="mb-4 rounded-full border border-neon/40 bg-neon/10 px-4 py-1 font-headline text-xs uppercase tracking-[0.22em] text-neon">
          Dataset Bias Detection
        </p>
        <h1 className="font-headline text-5xl font-bold uppercase tracking-tight text-white sm:text-7xl md:text-8xl">
          TrustLens AI
        </h1>
        <p className="mt-5 max-w-2xl text-base text-slate-light/90 sm:text-xl">
          Safe &amp; Trusted AI Starts With Fair Data
        </p>
        <Link
          href="/upload"
          className="btn-primary mt-10 text-base"
          style={{ pointerEvents: "auto" }}
        >
          Get Started
        </Link>
      </div>

      <style jsx>{`
        .trustlens-hero-fallback {
          background:
            radial-gradient(circle at 50% 42%, rgba(0, 209, 255, 0.22), transparent 22rem),
            radial-gradient(circle at 50% 55%, rgba(164, 230, 255, 0.12), transparent 30rem),
            linear-gradient(180deg, #020404 0%, #050606 48%, #101111 100%);
          perspective: 1200px;
        }

        .trustlens-grid {
          position: absolute;
          inset: auto -10% -18% -10%;
          height: 45%;
          background-image:
            linear-gradient(rgba(164, 230, 255, 0.18) 1px, transparent 1px),
            linear-gradient(90deg, rgba(164, 230, 255, 0.18) 1px, transparent 1px);
          background-size: 72px 72px;
          transform: rotateX(68deg);
          transform-origin: center bottom;
          opacity: 0.26;
          mask-image: linear-gradient(to top, black 0%, transparent 82%);
        }

        .trustlens-core {
          position: absolute;
          left: 50%;
          top: 46%;
          width: min(62vw, 760px);
          aspect-ratio: 1;
          transform: translate(-50%, -50%) rotateX(58deg) rotateZ(-12deg);
          transform-style: preserve-3d;
        }

        .trustlens-ring,
        .trustlens-prism,
        .trustlens-scanline {
          position: absolute;
          inset: 50%;
          transform-style: preserve-3d;
        }

        .trustlens-ring {
          width: 100%;
          height: 100%;
          border: 2px solid rgba(164, 230, 255, 0.72);
          border-radius: 50%;
          box-shadow:
            0 0 28px rgba(0, 209, 255, 0.45),
            inset 0 0 32px rgba(0, 209, 255, 0.18);
          transform: translate(-50%, -50%);
          animation: trustlens-spin 16s linear infinite;
        }

        .trustlens-ring-b {
          width: 74%;
          height: 74%;
          border-color: rgba(220, 184, 255, 0.6);
          transform: translate(-50%, -50%) rotateY(64deg);
          animation-duration: 12s;
          animation-direction: reverse;
        }

        .trustlens-ring-c {
          width: 48%;
          height: 48%;
          border-color: rgba(255, 255, 255, 0.52);
          transform: translate(-50%, -50%) rotateX(74deg);
          animation-duration: 9s;
        }

        .trustlens-prism {
          width: 28%;
          height: 28%;
          border: 1px solid rgba(255, 255, 255, 0.55);
          background:
            linear-gradient(135deg, rgba(255, 255, 255, 0.22), rgba(0, 209, 255, 0.06)),
            linear-gradient(45deg, rgba(0, 209, 255, 0.18), rgba(220, 184, 255, 0.14));
          box-shadow:
            0 0 54px rgba(0, 209, 255, 0.45),
            inset 0 0 32px rgba(255, 255, 255, 0.12);
          transform: translate(-50%, -50%) rotateX(58deg) rotateZ(45deg);
          animation: trustlens-pulse 4s ease-in-out infinite;
        }

        .trustlens-scanline {
          width: 82%;
          height: 2px;
          background: linear-gradient(90deg, transparent, rgba(164, 230, 255, 0.95), transparent);
          transform: translate(-50%, -50%) rotateZ(12deg);
          box-shadow: 0 0 22px rgba(0, 209, 255, 0.8);
          animation: trustlens-scan 5s ease-in-out infinite;
        }

        @keyframes trustlens-spin {
          from {
            rotate: 0deg;
          }
          to {
            rotate: 360deg;
          }
        }

        @keyframes trustlens-pulse {
          0%,
          100% {
            opacity: 0.64;
            scale: 0.92;
          }
          50% {
            opacity: 1;
            scale: 1.08;
          }
        }

        @keyframes trustlens-scan {
          0%,
          100% {
            opacity: 0;
            translate: 0 -180px;
          }
          50% {
            opacity: 1;
            translate: 0 180px;
          }
        }

        @media (max-width: 640px) {
          .trustlens-core {
            top: 42%;
            width: 120vw;
          }
        }
      `}</style>
    </header>
  );
}
