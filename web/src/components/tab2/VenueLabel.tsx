import { VENUE_LABELS } from "@/lib/corridors";
import { cn } from "@/lib/cn";
import { VENUE_COLORS } from "@/lib/theme";
import type { VenueName } from "@/lib/types";
import { VENUE_SHORT } from "./benchUtil";

/** Venue name with its small categorical swatch (colour identifies the venue, never grades it). */
export function VenueLabel({ venue, className }: { venue: VenueName; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap", className)} title={VENUE_LABELS[venue]}>
      <span aria-hidden className="inline-block h-2 w-2 shrink-0 rounded-[2px]" style={{ backgroundColor: VENUE_COLORS[venue] }} />
      {VENUE_SHORT[venue]}
    </span>
  );
}
