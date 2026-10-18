import { useState } from "react";
import { readFreights, readSnapshot } from "./api/client";
import { FleetMap } from "./components/FleetMap";
import { Freights } from "./components/Freights";
import { ProvenanceChips } from "./components/Provenance";
import { VehicleList } from "./components/VehicleList";
import { horaLima } from "./format";
import { usePolling } from "./usePolling";

export function App() {
  const poll = usePolling(readSnapshot, 2000);
  const freights = usePolling(readFreights, 5000);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"operacion" | "fletes">("operacion");
  const snap = poll.data;
  const vehicles = snap?.fleet.data.vehiculos ?? [];

  return (
    <div className="app">
      <header className="top">
        <h1>Fleet Intelligence</h1>
        <nav className="tabs" role="tablist" aria-label="Vistas">
          <button type="button" role="tab" aria-selected={view === "operacion"} onClick={() => setView("operacion")}>Operación</button>
          <button type="button" role="tab" aria-selected={view === "fletes"} onClick={() => setView("fletes")}>Fletes</button>
        </nav>
        {snap && (
          <div className="replaybar" aria-label="Estado del replay">
            <span className={`chip replay-${snap.replay.data.estado}`}>
              {snap.replay.data.estado === "playing" ? "Replay en curso" : "Replay en pausa"}
            </span>
            <span className="dato">Hora de replay {horaLima(snap.replay.data.hora_replay)}</span>
            <span className="dato">Velocidad {snap.replay.data.velocidad}x</span>
            <ProvenanceChips items={snap.fleet.provenance} />
          </div>
        )}
      </header>
      <p className="banner" role="note">
        Replay de una flota simulada sobre carreteras reales de Perú: telemetría, fletes, conductores y mensajes sintéticos. No es tiempo real.
      </p>
      {view === "fletes" && (
        <>
          {freights.status === "error" && <p className="alert" role="alert">No se pudo leer la Domain API</p>}
          {freights.status === "loading" && <p className="state">Cargando…</p>}
          {freights.data && <Freights board={freights.data} />}
        </>
      )}
      {view === "operacion" && poll.status === "error" && (
        <p className="alert" role="alert">No se pudo leer la Domain API</p>
      )}
      {view === "operacion" && poll.status === "loading" && <p className="state">Cargando…</p>}
      {view === "operacion" && snap && vehicles.length === 0 && <p className="state">Sin vehículos en el replay</p>}
      {view === "operacion" && snap && vehicles.length > 0 && (
        <main className="grid">
          <section aria-label="Vehículos y viajes">
            <h2>Vehículos</h2>
            <p className="dato">
              {snap.fleet.data.total_vehiculos} vehículos · {snap.fleet.data.viajes_en_curso} viajes en curso · {snap.fleet.data.alertas_abiertas} alertas abiertas
            </p>
            <VehicleList snapshot={snap} selected={selected} onSelect={setSelected} />
          </section>
          <section aria-label="Mapa">
            <FleetMap vehicles={vehicles} selected={selected} onSelect={setSelected} />
          </section>
        </main>
      )}
    </div>
  );
}
