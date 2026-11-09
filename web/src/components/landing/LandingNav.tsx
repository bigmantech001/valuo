import Link from "next/link";

const LINKS: Array<{ href: string; label: string }> = [
  { href: "#findings", label: "Findings" },
  { href: "#questions", label: "Questions" },
  { href: "#method", label: "Method" },
  { href: "#bear", label: "Bear case" },
  { href: "#reproduce", label: "Reproduce" },
];

/** Thin sticky header: serif wordmark on the left, section anchors on the right. */
export function LandingNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-canvas/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-none items-center gap-8 px-6 lg:px-[1.25vw]">
        <Link href="/" className="font-serif text-[22px] font-medium leading-none tracking-tight text-ink">
          Valuo
        </Link>
        <nav aria-label="Sections" className="ml-auto hidden items-center gap-6 md:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="text-[14px] text-muted transition-colors hover:text-ink">
              {l.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
