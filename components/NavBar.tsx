import Link from "next/link";

type NavBarProps = {
  active?: "home" | "upload" | "results";
};

const navItems: Array<{ href: string; label: string; key: NavBarProps["active"] }> = [
  { href: "/", label: "Home", key: "home" },
  { href: "/upload", label: "Upload", key: "upload" },
  { href: "/results/latest", label: "Results", key: "results" }
];

export function NavBar({ active }: NavBarProps) {
  return (
    <nav className="fixed top-0 z-50 w-full border-b border-white/10 bg-void/45 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-8">
        <Link href="/" className="font-headline text-lg font-bold uppercase tracking-[0.16em] text-neon">
          TrustLens AI
        </Link>

        <div className="hidden items-center gap-6 text-sm md:flex">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-full px-4 py-1.5 font-headline uppercase tracking-[0.12em] transition ${
                active === item.key
                  ? "border border-neon/60 bg-neon/10 text-neon"
                  : "text-slate-light/80 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <Link href="/upload" className="btn-primary text-xs sm:text-sm">
          Get Started
        </Link>
      </div>
    </nav>
  );
}

