#!/usr/bin/env node
/**
 * write-build-info.mjs — emit immutable build metadata into a frontend dist/.
 *
 * PILOT-DEPLOYMENT-READINESS-001B (SCOPE D).
 *
 * Reads RMP_VERSION / RMP_GIT_SHA / RMP_BUILD_TIME from the environment
 * (injected by the Docker build or CI), falling back to honest
 * "dev"/"unknown" placeholders when absent.  Writes build-info.json into the
 * target directory so the served static app exposes version identity for
 * deployment verification.
 *
 * Usage:
 *   node scripts/write-build-info.mjs <dist-dir>
 *
 * The file is always overwritten. Never emits secrets or env dumps.
 */
import { writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

const dist = resolve(process.argv[2] || "dist");
const version = process.env.RMP_VERSION || "dev";
const gitSha = process.env.RMP_GIT_SHA || "unknown";
const buildTime = process.env.RMP_BUILD_TIME || "unknown";

const info = {
  version,
  git_sha: gitSha,
  build_time: buildTime,
};

mkdirSync(dist, { recursive: true });
writeFileSync(resolve(dist, "build-info.json"), JSON.stringify(info, null, 2) + "\n");

process.stdout.write(`build-info.json → ${dist} (version=${version}, sha=${gitSha})\n`);
