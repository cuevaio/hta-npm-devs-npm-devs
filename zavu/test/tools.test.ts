import { describe, expect, it, vi } from "vitest";
import { TOOL_DEFS, callDomainApi } from "../tools";

const KEY = "clave-de-prueba";
const env = () => ({ DOMAIN_API_URL: process.env.DOMAIN_API_URL, DOMAIN_API_KEY: KEY });
const ARGS: Record<string, Record<string, string>> = {
  get_vehicle_status: { alias: "T03" },
  get_trip_status: { trip_id: "V-001" },
  get_fuel_analysis: { trip_id: "V-001" },
  get_operational_bottlenecks: { trip_id: "V-001" },
};

describe("TOOL_DEFS", () => {
  it("tiene exactamente las 6 tools de lectura, sin control_replay", () => {
    expect(TOOL_DEFS.map((t) => t.name).sort()).toEqual([
      "get_alerts",
      "get_fleet_overview",
      "get_fuel_analysis",
      "get_operational_bottlenecks",
      "get_trip_status",
      "get_vehicle_status",
    ]);
  });
});

describe("contra el servidor simulado del contrato", () => {
  for (const def of TOOL_DEFS) {
    it(`${def.name} devuelve el sobre con procedencia, rango y updated_at`, async () => {
      const out = (await callDomainApi(def.name, ARGS[def.name] ?? {}, env())) as Record<string, unknown>;
      expect(out.error).toBeUndefined();
      expect(out).toHaveProperty("provenance");
      expect(out).toHaveProperty("time_range");
      expect(out).toHaveProperty("updated_at");
    });
  }

  it("hace una sola petición, a /v1/tools/<tool>, con X-API-Key", async () => {
    const spy = vi.fn(fetch);
    await callDomainApi("get_trip_status", { trip_id: "V-001" }, env(), spy);
    expect(spy).toHaveBeenCalledTimes(1);
    const [url, init] = spy.mock.calls[0];
    expect(new URL(String(url)).pathname).toBe("/v1/tools/get_trip_status");
    expect(new URL(String(url)).searchParams.get("trip_id")).toBe("V-001");
    expect((init!.headers as Record<string, string>)["X-API-Key"]).toBe(KEY);
  });

  it("sin API key la Domain API responde 401 y la tool no devuelve datos", async () => {
    const noKey = (u: string | URL | Request, init?: RequestInit) =>
      fetch(u, { ...init, headers: {} });
    const out = (await callDomainApi("get_alerts", {}, env(), noKey)) as { error: string; status: number };
    expect(out.status).toBe(401);
    expect(out.error).toBeTruthy();
  });

  it("ante un alias desconocido devuelve error con detail, nunca un valor por defecto", async () => {
    const out = (await callDomainApi("get_vehicle_status", { alias: "ZZZ" }, env())) as Record<string, unknown>;
    if (out.status === undefined) {
      // Prism sirve el example aunque el alias no exista: se verifica el 404 con un fetch simulado
      const notFound = async () =>
        new Response(JSON.stringify({ detail: "Vehículo no encontrado" }), { status: 404 });
      const err = (await callDomainApi("get_vehicle_status", { alias: "ZZZ" }, env(), notFound as typeof fetch)) as Record<string, unknown>;
      expect(err).toMatchObject({ status: 404, detail: "Vehículo no encontrado" });
      expect(err).not.toHaveProperty("provenance");
    } else {
      expect(out).toHaveProperty("detail");
    }
  });
});

describe("configuración incompleta", () => {
  it("sin DOMAIN_API_URL no hace fetch y devuelve un error claro", async () => {
    const spy = vi.fn(fetch);
    const out = (await callDomainApi("get_alerts", {}, { DOMAIN_API_KEY: KEY }, spy)) as { error: string };
    expect(spy).not.toHaveBeenCalled();
    expect(out.error).toMatch(/DOMAIN_API_URL/);
  });

  it("sin DOMAIN_API_KEY no hace fetch", async () => {
    const spy = vi.fn(fetch);
    await callDomainApi("get_alerts", {}, { DOMAIN_API_URL: "http://x" }, spy);
    expect(spy).not.toHaveBeenCalled();
  });
});
