import type { Manifest, Snapshot } from "@/lib/types";

/** Props every tab component receives from `src/app/terminal/page.tsx`. */
export interface TabProps {
  snapshot: Snapshot;
  manifest: Manifest | null;
}
