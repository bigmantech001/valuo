import "server-only";
import { existsSync, promises as fs } from "node:fs";
import path from "node:path";
import { serverEnv } from "./env";
import { sha256Hex } from "./hash";
import type { Integrity, Manifest, Snapshot } from "./types";

/**
 * Server-only loader for the canonical artifacts written by `python -m valuo.reproduce`.
 * Resolution order for the artifacts directory: `VALUO_ARTIFACTS_DIR` (process env, then
 * repo-root `.env`) else `<cwd>/../artifacts`. Every loader returns `null` when the file is
 * missing or unparsable so the page can render the "run make reproduce" empty state instead
 * of crashing; nothing is ever substituted for a missing artifact.
 */

export interface ArtifactPaths {
  dir: string;
  snapshot: string;
  manifest: string;
  memo: string;
}

export function artifactsDir(): string {
  const fromEnv = serverEnv("VALUO_ARTIFACTS_DIR");
  if (fromEnv) return path.resolve(fromEnv);
  const sibling = path.resolve(process.cwd(), "..", "artifacts");
  if (existsSync(sibling)) return sibling;
  // Deployments rooted at web/ (Vercel): scripts/bundle-data.mjs copies the committed artifacts here at build time.
  return path.resolve(process.cwd(), ".valuo-data", "artifacts");
}

export function artifactPaths(): ArtifactPaths {
  const dir = artifactsDir();
  return {
    dir,
    snapshot: path.join(dir, "latest_snapshot.json"),
    manifest: path.join(dir, "manifest.json"),
    memo: path.join(dir, "IC_MEMO.md"),
  };
}

interface CacheEntry<T> {
  mtimeMs: number;
  size: number;
  value: T;
}
const parsedCache = new Map<string, CacheEntry<unknown>>();

async function readJsonCached<T>(file: string): Promise<T | null> {
  let stat;
  try {
    stat = await fs.stat(file);
  } catch {
    return null;
  }
  const hit = parsedCache.get(file) as CacheEntry<T> | undefined;
  if (hit && hit.mtimeMs === stat.mtimeMs && hit.size === stat.size) return hit.value;
  try {
    const text = await fs.readFile(file, "utf8");
    const value = JSON.parse(text) as T;
    parsedCache.set(file, { mtimeMs: stat.mtimeMs, size: stat.size, value });
    return value;
  } catch {
    return null;
  }
}

export async function loadSnapshot(): Promise<Snapshot | null> {
  const parsed = await readJsonCached<Snapshot>(artifactPaths().snapshot);
  return parsed && typeof parsed === "object" && "near_rpc" in parsed ? parsed : null;
}

export async function loadManifest(): Promise<Manifest | null> {
  const parsed = await readJsonCached<Manifest>(artifactPaths().manifest);
  return parsed && typeof parsed === "object" && Array.isArray(parsed.records) ? parsed : null;
}

export async function loadArtifacts(): Promise<{ snapshot: Snapshot | null; manifest: Manifest | null }> {
  const [snapshot, manifest] = await Promise.all([loadSnapshot(), loadManifest()]);
  return { snapshot, manifest };
}

/** Exact bytes of latest_snapshot.json (for download / hashing), or null when missing. */
export async function readSnapshotBytes(): Promise<Buffer | null> {
  try {
    return await fs.readFile(artifactPaths().snapshot);
  } catch {
    return null;
  }
}

export async function readMemo(): Promise<string | null> {
  try {
    return await fs.readFile(artifactPaths().memo, "utf8");
  } catch {
    return null;
  }
}

/** Recompute sha256 over the snapshot file bytes and compare with the manifest's recorded digest. */
export async function computeIntegrity(manifest: Manifest | null): Promise<Integrity> {
  const paths = artifactPaths();
  const bytes = await readSnapshotBytes();
  const fileSha = bytes ? sha256Hex(bytes) : null;
  const manifestSha = manifest?.snapshot_sha256 ?? null;
  return {
    snapshot_sha256_file: fileSha,
    snapshot_sha256_manifest: manifestSha,
    matches: fileSha && manifestSha ? fileSha === manifestSha : null,
    snapshot_path: paths.snapshot,
    manifest_path: paths.manifest,
  };
}

export async function artifactsPresent(): Promise<boolean> {
  try {
    await fs.access(artifactPaths().snapshot);
    return true;
  } catch {
    return false;
  }
}
