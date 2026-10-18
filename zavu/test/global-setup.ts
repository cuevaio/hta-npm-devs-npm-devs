import { spawn, type ChildProcess } from "node:child_process";

const PORT = 4011;
let prism: ChildProcess | undefined;

export async function setup() {
  prism = spawn(
    "npx",
    ["-y", "@stoplight/prism-cli@5", "mock", "-p", String(PORT), "../backend/openapi.json"],
    { stdio: "ignore", detached: true },
  );
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    try {
      await fetch(`http://127.0.0.1:${PORT}/v1/tools/get_alerts`);
      process.env.DOMAIN_API_URL = `http://127.0.0.1:${PORT}`;
      return;
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  throw new Error("Prism no respondió a tiempo");
}

export async function teardown() {
  if (prism?.pid) process.kill(-prism.pid);
}
