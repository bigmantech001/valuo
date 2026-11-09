"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { buildManifestIndex, type ManifestIndex } from "@/lib/manifestIndex";
import type { Manifest } from "@/lib/types";

const Ctx = createContext<ManifestIndex | null>(null);
const EMPTY = buildManifestIndex(null);

/** Makes the manifest available to client components (ProvenanceBadge) without prop drilling. */
export function ManifestProvider({ manifest, children }: { manifest: Manifest | null; children: ReactNode }) {
  const index = useMemo(() => buildManifestIndex(manifest), [manifest]);
  return <Ctx.Provider value={index}>{children}</Ctx.Provider>;
}

/** The manifest index from context, or an empty index when no provider is mounted. */
export function useManifestIndex(): ManifestIndex {
  return useContext(Ctx) ?? EMPTY;
}
