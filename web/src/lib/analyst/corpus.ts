import "server-only";
import { computeIntegrity, loadArtifacts, readMemo } from "@/lib/snapshot";
import type { Manifest, Snapshot } from "@/lib/types";
import { buildCorpus, suggestQuestions, type Corpus } from "./retrieval";

export interface LoadedCorpus {
  corpus: Corpus;
  snapshot: Snapshot;
  manifest: Manifest | null;
  /** sha256 of the snapshot bytes on disk (what the answer is grounded on) */
  snapshotSha256: string | null;
  /** manifest digest agrees with the file bytes (null when either is missing) */
  integrityMatches: boolean | null;
  memoSha256: string | null;
  nMemoSections: number;
  suggestions: string[];
}

let cache: { key: string; value: LoadedCorpus } | null = null;

/**
 * Load the artifacts and build the retrieval corpus, rebuilt only when the snapshot bytes, the
 * manifest or the memo change. Returns null without a snapshot.
 */
export async function loadCorpus(): Promise<LoadedCorpus | null> {
  const { snapshot, manifest } = await loadArtifacts();
  if (!snapshot) return null;
  const [integrity, memo] = await Promise.all([computeIntegrity(manifest), readMemo()]);
  const key = `${integrity.snapshot_sha256_file}|${manifest?.generated_at_utc ?? ""}|${memo?.length ?? 0}`;
  if (cache && cache.key === key) return cache.value;
  const corpus = buildCorpus(snapshot, manifest, memo);
  const value: LoadedCorpus = {
    corpus,
    snapshot,
    manifest,
    snapshotSha256: integrity.snapshot_sha256_file,
    integrityMatches: integrity.matches,
    memoSha256: manifest?.memo_sha256 ?? null,
    nMemoSections: corpus.facts.filter((f) => f.kind === "memo").length,
    suggestions: suggestQuestions(snapshot),
  };
  cache = { key, value };
  return value;
}
