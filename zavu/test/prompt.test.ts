import { describe, expect, it } from "vitest";
import { PROMPT } from "../prompt";

describe("prompt del agente", () => {
  it("limita el alcance a la flota y rechaza lo ajeno", () => {
    expect(PROMPT).toMatch(/Solo la operación de la flota/);
    expect(PROMPT).toMatch(/rechazas en una frase/);
    expect(PROMPT).toMatch(/sin responder primero/);
  });

  it("no conserva restos del soporte genérico", () => {
    expect(PROMPT).not.toMatch(/\b(orden|órdenes|pedido|reembolso|refund|escalate|lookup_order)\b|\bAda\b/i);
  });

  it("separa hechos de hipótesis, declara procedencia y hora, y no inventa", () => {
    expect(PROMPT).toMatch(/Hechos/);
    expect(PROMPT).toMatch(/Hipótesis/);
    expect(PROMPT).toMatch(/procedencia/i);
    expect(PROMPT).toMatch(/hora de Lima \(UTC−5\)/);
    expect(PROMPT).toMatch(/replay/i);
    expect(PROMPT).toMatch(/Nunca inventes/);
    expect(PROMPT).toMatch(/Nunca decides por el gestor/);
  });
});
