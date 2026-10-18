import { afterEach, describe, expect, it, vi } from "vitest";
import { contractExamples, initializeParams, mockUpstream, rpc } from "./helpers";

const examples = contractExamples();
const TOOLS = [
  "get_fleet_overview",
  "get_vehicle_status",
  "get_trip_status",
  "get_fuel_analysis",
  "get_operational_bottlenecks",
  "get_alerts",
  "get_vehicle_metrics",
  "control_replay",
];

afterEach(() => vi.restoreAllMocks());

async function call(name: string, args: Record<string, unknown>) {
  const { json } = await rpc("tools/call", { name, arguments: args });
  return json.result;
}

describe("tools/list", () => {
  it("responde initialize", async () => {
    const { status, json } = await rpc("initialize", initializeParams);
    expect(status).toBe(200);
    expect(json.result.serverInfo.name).toBe("certera");
  });

  it("lista exactamente las 8 tools con su esquema de entrada", async () => {
    const { json } = await rpc("tools/list", {});
    const tools = json.result.tools as { name: string; description: string; inputSchema: any }[];
    expect(tools.map((t) => t.name).sort()).toEqual([...TOOLS].sort());
    const by = Object.fromEntries(tools.map((t) => [t.name, t]));
    expect(by.get_vehicle_status!.inputSchema.required).toEqual(["alias"]);
    for (const n of ["get_trip_status", "get_fuel_analysis", "get_operational_bottlenecks"]) {
      expect(by[n]!.inputSchema.required).toEqual(["trip_id"]);
    }
    expect(by.get_vehicle_metrics!.inputSchema.required).toEqual(["alias"]);
    expect(by.get_vehicle_metrics!.inputSchema.properties.agrupar_por.enum).toEqual(["dia", "viaje"]);
    expect(by.control_replay!.inputSchema.required).toEqual(["action"]);
    expect(by.control_replay!.inputSchema.properties.action.enum).toEqual([
      "play", "pause", "seek", "set_speed",
    ]);
    for (const t of tools) expect(t.description).toMatch(/replay|Replay/);
  });
});

describe("tools/call", () => {
  const getCases: [string, Record<string, string>][] = [
    ["get_fleet_overview", {}],
    ["get_alerts", {}],
    ["get_vehicle_status", { alias: "T03" }],
    ["get_trip_status", { trip_id: "V-001" }],
    ["get_fuel_analysis", { trip_id: "V-001" }],
    ["get_operational_bottlenecks", { trip_id: "V-001" }],
    ["get_vehicle_metrics", { alias: "T07" }],
    ["get_vehicle_metrics", { alias: "T07", desde: "2020-04-01", hasta: "2020-04-19", agrupar_por: "viaje" }],
  ];

  it.each(getCases)("%s devuelve el sobre del contrato tal cual", async (name, args) => {
    const calls = mockUpstream();
    const result = await call(name, args);
    expect(result.isError).toBeFalsy();
    expect(JSON.parse(result.content[0].text)).toEqual(examples[`/v1/tools/${name}`]);
    expect(result.structuredContent).toEqual(examples[`/v1/tools/${name}`]);
    expect(calls).toHaveLength(1);
    expect(calls[0]).toMatchObject({
      method: "GET",
      path: `/v1/tools/${name}`,
      query: args,
      apiKey: "clave-servicio-de-prueba",
    });
  });

  it("control_replay hace POST con el cuerpo", async () => {
    const calls = mockUpstream();
    const args = { action: "seek", to_event_time: "2024-05-01T10:00:00Z" };
    const result = await call("control_replay", args);
    expect(JSON.parse(result.content[0].text)).toEqual(examples["/v1/tools/control_replay"]);
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/v1/tools/control_replay",
      body: args,
      apiKey: "clave-servicio-de-prueba",
    });
  });

  it("un 404 del upstream llega como isError con el detail", async () => {
    mockUpstream((c) => (c.query.alias === "T99" ? "Vehículo T99 no existe" : null));
    const result = await call("get_vehicle_status", { alias: "T99" });
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toBe("Vehículo T99 no existe");
  });

  it("rechaza argumentos fuera del esquema sin llamar al upstream", async () => {
    const calls = mockUpstream();
    const result = await call("control_replay", { action: "rewind" });
    expect(result.isError).toBe(true);
    expect((await call("get_vehicle_metrics", { alias: "T07", agrupar_por: "semana" })).isError).toBe(true);
    expect((await call("get_vehicle_metrics", { alias: "T07", desde: "13/04/2020" })).isError).toBe(true);
    expect(calls).toHaveLength(0);
  });
});
