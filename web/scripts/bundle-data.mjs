// Copies the committed pipeline outputs into web/.valuo-data/ so a deployment whose root is web/
// (e.g. Vercel) can read them at runtime. Local development keeps reading ../artifacts directly;
// the runtime only falls back to .valuo-data when ../artifacts is absent. Nothing is generated here.
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";

const web = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const repo = path.resolve(web, "..");
const out = path.join(web, ".valuo-data");

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

const artifacts = path.join(repo, "artifacts");
if (existsSync(artifacts)) {
  cpSync(artifacts, path.join(out, "artifacts"), {
    recursive: true,
    filter: (src) => !src.includes(`${path.sep}dev`) && !src.endsWith(".duckdb") && !src.endsWith(".duckdb.wal"),
  });
}
const workflows = path.join(repo, ".github", "workflows");
if (existsSync(workflows)) cpSync(workflows, path.join(out, ".github", "workflows"), { recursive: true });

console.log(`bundle-data: ${existsSync(artifacts) ? "artifacts" : "no artifacts"}, ${existsSync(workflows) ? "workflows" : "no workflows"} -> ${path.relative(web, out)}`);
