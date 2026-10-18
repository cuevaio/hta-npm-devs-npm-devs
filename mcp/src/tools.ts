import { McpServer } from "@modelcontextprotocol/server";
import { z } from "zod";
import type { components } from "./api/types";
import { callTool, type DomainApiEnv } from "./domain-api";

type ControlReplayBody = components["schemas"]["ControlReplayRequest"];

const REPLAY =
  "Los datos son un replay de telemetría histórica de una flota simulada en Perú, nunca tiempo real. " +
  "La respuesta es un sobre con procedencia, rango de tiempo y updated_at.";

const tripId = z.string().describe("Identificador del viaje, p. ej. V-001");

export function createServer(env: DomainApiEnv): McpServer {
  const server = new McpServer({ name: "certera", version: "1.0.0" });

  // Adaptador delgado: llama a la Domain API y devuelve el sobre sin tocarlo.
  const adapt =
    (name: string) =>
    async (args: Record<string, unknown>) => {
      const result = await callTool(env, name, args);
      const text = typeof result.body === "string" ? result.body : JSON.stringify(result.body);
      if (!result.ok) {
        const detail =
          typeof result.body === "object" && result.body !== null && "detail" in result.body
            ? (result.body as { detail: unknown }).detail
            : result.body;
        return {
          isError: true,
          content: [
            {
              type: "text" as const,
              text: typeof detail === "string" ? detail : JSON.stringify(detail),
            },
          ],
        };
      }
      const structured =
        typeof result.body === "object" && result.body !== null && !Array.isArray(result.body)
          ? (result.body as Record<string, unknown>)
          : undefined;
      return {
        content: [{ type: "text" as const, text }],
        ...(structured ? { structuredContent: structured } : {}),
      };
    };

  server.registerTool(
    "get_fleet_overview",
    {
      description: `Resumen de la flota: estado de cada vehículo y viajes en curso del replay. ${REPLAY}`,
      inputSchema: z.object({}),
    },
    adapt("get_fleet_overview"),
  );

  server.registerTool(
    "get_vehicle_status",
    {
      description: `Estado de un vehículo (alias anónimo T01…T28): viaje actual, sentido, posición y última lectura. ${REPLAY}`,
      inputSchema: z.object({ alias: z.string().describe("Alias del vehículo, p. ej. T03") }),
    },
    adapt("get_vehicle_status"),
  );

  server.registerTool(
    "get_trip_status",
    {
      description: `Estado de un viaje: vehículo, corredor, sentido, avance por tramo y paradas. ${REPLAY}`,
      inputSchema: z.object({ trip_id: tripId }),
    },
    adapt("get_trip_status"),
  );

  server.registerTool(
    "get_fuel_analysis",
    {
      description: `Análisis de combustible de un viaje: consumo por tramo frente a la línea base de sus pares en el mismo sentido y sobreconsumo detectado. ${REPLAY}`,
      inputSchema: z.object({ trip_id: tripId }),
    },
    adapt("get_fuel_analysis"),
  );

  server.registerTool(
    "get_operational_bottlenecks",
    {
      description: `Cuellos de botella de un viaje: tiempo perdido por paradas sin explicar o ralentí prolongado, ordenado por impacto. ${REPLAY}`,
      inputSchema: z.object({ trip_id: tripId }),
    },
    adapt("get_operational_bottlenecks"),
  );

  server.registerTool(
    "get_alerts",
    {
      description: `Alertas vigentes de la flota (sobreconsumo, cuellos de botella) con su procedencia. ${REPLAY}`,
      inputSchema: z.object({}),
    },
    adapt("get_alerts"),
  );

  server.registerTool(
    "control_replay",
    {
      description:
        "Controla el replay de telemetría histórica (nunca tiempo real): play, pause, seek (requiere to_event_time, hora del evento en UTC) o set_speed (requiere speed > 0).",
      inputSchema: z.object({
        action: z.enum(["play", "pause", "seek", "set_speed"]),
        speed: z.number().positive().optional().describe("Requerido con set_speed"),
        to_event_time: z.iso
          .datetime()
          .optional()
          .describe("Requerido con seek (hora del evento, UTC)"),
      }),
    },
    (args) => adapt("control_replay")(args satisfies ControlReplayBody),
  );

  return server;
}
