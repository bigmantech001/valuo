import type { NextConfig } from "next";

/**
 * `next dev` and `next build` / `next start` must never share an output directory. A dev server left
 * running rewrites `.next/server/app-paths-manifest.json` under a finished production build, and the
 * started server then answers 404 for routes the build emitted (/api/live-benchmark, /api/reproduce/status).
 * Development therefore writes to `.next-dev`; production keeps `.next`.
 */
const nextConfig: NextConfig = {
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
  // Server code reads the committed pipeline outputs with fs at runtime; include the build-time copy in every
  // server bundle (see scripts/bundle-data.mjs).
  outputFileTracingIncludes: { "/**": ["./.valuo-data/**/*"] },
};

export default nextConfig;
