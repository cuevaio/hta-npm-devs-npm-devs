import { exports } from "cloudflare:workers";
import { describe, expect, it } from "vitest";

describe("worker", () => {
  it("responde /health", async () => {
    const response = await exports.default.fetch("https://mcp.test/health");

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  });

  it("responde 404 en rutas desconocidas", async () => {
    const response = await exports.default.fetch("https://mcp.test/nada");

    expect(response.status).toBe(404);
  });
});
