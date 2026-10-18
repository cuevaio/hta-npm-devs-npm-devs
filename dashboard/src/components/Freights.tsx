import { useState } from "react";
import type { Aggregate, FreightBoardResponse, Freight } from "../api/client";
import { horaLima, pen } from "../format";
import { ProvenanceChips } from "./Provenance";

const ESTADO_FLETE: Record<Freight["estado"], string> = {
  programado: "Programado",
  en_curso: "En curso",
  finalizado: "Finalizado",
};

type Tip = { x: number; y: number; lines: string[] } | null;

/** Barras apiladas combustible + margen = ingresos (sin IGV), una por grupo. */
function StackedBars({ title, rows, horizontal, onTip }: {
  title: string;
  rows: Aggregate[];
  horizontal: boolean;
  onTip: (t: Tip) => void;
}) {
  const max = Math.max(1, ...rows.map((r) => r.ingresos_pen));
  const tip = (e: React.MouseEvent, r: Aggregate) =>
    onTip({
      x: e.clientX,
      y: e.clientY,
      lines: [
        r.clave,
        `Ingresos ${pen(r.ingresos_pen)} · ${r.fletes} fletes`,
        `Combustible ${pen(r.combustible_pen)}`,
        `Margen ${pen(r.margen_pen)}${r.margen_pct != null ? ` (${r.margen_pct.toFixed(1)} %)` : ""}`,
      ],
    });
  return (
    <figure className="viz" aria-label={title}>
      <figcaption>
        <span>{title}</span>
        <span className="legend" aria-hidden="true">
          <span><i className="sw sw-combustible" />Combustible</span>
          <span><i className="sw sw-margen" />Margen</span>
        </span>
      </figcaption>
      <div className={horizontal ? "hbars" : "vbars"}>
        {rows.map((r) => {
          const fuel = (r.combustible_pen / max) * 100;
          const margin = (Math.max(0, r.margen_pen) / max) * 100;
          return (
            <div
              key={r.clave}
              className="bar"
              data-clave={r.clave}
              onMouseMove={(e) => tip(e, r)}
              onMouseLeave={() => onTip(null)}
            >
              <span className="bar-label">{horizontal ? r.clave : r.clave.slice(5)}</span>
              <span className="bar-track">
                <span className="seg seg-combustible" style={horizontal ? { width: `${fuel}%` } : { height: `${fuel}%` }} />
                <span className="seg seg-margen" style={horizontal ? { width: `${margin}%` } : { height: `${margin}%` }} />
              </span>
              {horizontal && (
                <span className="bar-value">
                  {pen(r.ingresos_pen)} · {r.margen_pct != null ? `${r.margen_pct.toFixed(0)} %` : "–"}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </figure>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{value}</strong>
      {sub && <span className="dato">{sub}</span>}
    </div>
  );
}

export function Freights({ board }: { board: FreightBoardResponse }) {
  const [tipState, setTip] = useState<Tip>(null);
  const d = board.data;
  const r = d.resumen;
  // en curso, luego finalizados (el más reciente arriba) y al final los programados (el más próximo arriba)
  const rank = { en_curso: 0, finalizado: 1, programado: 2 } as const;
  const fletes = [...d.fletes].sort((a, b) =>
    rank[a.estado] - rank[b.estado] ||
    (a.estado === "programado" ? a.salida.localeCompare(b.salida) : b.salida.localeCompare(a.salida)));
  return (
    <main className="freights" aria-label="Fletes">
      <div className="freights-head">
        <h2>Fletes</h2>
        <span className="dato">Hasta {horaLima(board.time_range.to)} · montos sin IGV, en soles</span>
        <ProvenanceChips items={board.provenance} />
      </div>
      <section className="kpis" aria-label="Resumen de fletes finalizados">
        <Kpi label="Ingresos" value={pen(r.ingresos_pen)} sub={`${r.fletes} finalizados · ${r.toneladas.toFixed(0)} t`} />
        <Kpi label="Combustible" value={pen(r.combustible_pen)} sub={`${r.litros.toLocaleString("es-PE", { maximumFractionDigits: 0 })} L`} />
        <Kpi label="Margen tras combustible" value={pen(r.margen_pen)} sub={r.margen_pct != null ? `${r.margen_pct.toFixed(1)} % de los ingresos` : "–"} />
        <Kpi label="Rendimiento" value={r.l_100km != null ? `${r.l_100km.toFixed(1)} L/100 km` : "–"} sub={`${r.km.toLocaleString("es-PE", { maximumFractionDigits: 0 })} km`} />
        <Kpi label="Detracción (4 %)" value={pen(r.detraccion_pen)} sub={`IGV ${pen(r.igv_pen)}`} />
        <Kpi label="En operación" value={`${r.en_curso} en curso`} sub={`${r.programados} programados`} />
      </section>
      {r.fletes === 0 ? (
        <p className="state">Aún no hay fletes finalizados en el replay</p>
      ) : (
        <div className="charts">
          <StackedBars title="Ingresos por corredor" rows={d.por_corredor} horizontal onTip={setTip} />
          <StackedBars title="Ingresos por día de llegada" rows={d.por_dia} horizontal={false} onTip={setTip} />
        </div>
      )}
      <section aria-label="Por vehículo">
        <h3>Por vehículo</h3>
        <div className="table-wrap">
          <table className="table" data-table="vehiculos">
            <thead>
              <tr><th>Vehículo</th><th>Fletes</th><th>t</th><th>L/100 km</th><th>Ingresos</th><th>Combustible</th><th>Margen</th></tr>
            </thead>
            <tbody>
              {d.por_vehiculo.map((v) => (
                <tr key={v.clave}>
                  <td>{v.clave}</td><td>{v.fletes}</td><td>{v.toneladas.toFixed(0)}</td>
                  <td>{v.l_100km?.toFixed(1) ?? "–"}</td><td>{pen(v.ingresos_pen)}</td>
                  <td>{pen(v.combustible_pen)}</td>
                  <td>{pen(v.margen_pen)} <span className="dato">{v.margen_pct?.toFixed(0) ?? "–"} %</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section aria-label="Detalle de fletes">
        <h3>Detalle de fletes</h3>
        <div className="table-wrap">
          <table className="table" data-table="fletes">
            <thead>
              <tr>
                <th>Flete</th><th>Estado</th><th>Vehículo</th><th>Cliente</th><th>Carga</th><th>Ruta</th>
                <th>Salida</th><th>GRE</th><th>Tarifa</th><th>Detracción</th><th>L/100 km</th><th>Combustible</th><th>Margen</th>
              </tr>
            </thead>
            <tbody>
              {fletes.map((f) => (
                <tr key={f.flete_id} data-flete={f.flete_id}>
                  <td>{f.flete_id}<br /><span className="dato">{f.viaje_id}</span></td>
                  <td><span className={`chip flete-${f.estado}`}>{ESTADO_FLETE[f.estado]}</span></td>
                  <td>{f.vehiculo}<br /><span className="dato">{f.conductor ?? ""}</span></td>
                  <td>{f.cliente}<br /><span className="dato">RUC {f.ruc_cliente ?? "–"}</span></td>
                  <td>{f.carga}<br /><span className="dato">{f.toneladas?.toFixed(1) ?? "–"} t</span></td>
                  <td>{f.origen} → {f.destino}<br /><span className="dato">{f.corredor}</span></td>
                  <td className="dato">{horaLima(f.salida)}</td>
                  <td className="dato">{f.gre_transportista ?? "–"}</td>
                  <td>{pen(f.tarifa_pen)}</td>
                  <td>{pen(f.detraccion_pen)}</td>
                  <td>{f.l_100km?.toFixed(1) ?? "–"}</td>
                  <td>{pen(f.combustible_pen)}</td>
                  <td>{pen(f.margen_pen)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {tipState && (
        <div className="tooltip" role="tooltip" style={{ left: tipState.x + 12, top: tipState.y + 12 }}>
          {tipState.lines.map((l, i) => (i === 0 ? <strong key={i}>{l}</strong> : <span key={i}>{l}</span>))}
        </div>
      )}
    </main>
  );
}
