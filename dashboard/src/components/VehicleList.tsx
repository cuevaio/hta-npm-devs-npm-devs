import type { Snapshot } from "../api/client";
import { ESTADO, horaLima, isStale, msnm } from "../format";

type Props = {
  snapshot: Snapshot;
  selected: string | null;
  onSelect: (alias: string) => void;
};

export function VehicleList({ snapshot, selected, onSelect }: Props) {
  const { fleet, replay, trips } = snapshot;
  return (
    <ul className="vehicles">
      {fleet.data.vehiculos.map((v, i) => {
        const trip = v.viaje_id ? trips[v.viaje_id] : undefined;
        const stale = isStale(v.hora_evento, replay.data.hora_replay);
        const lectura = [msnm(v.altitud_m), horaLima(v.hora_evento)].filter(Boolean).join(" · ");
        return (
          <li key={v.alias} style={{ "--i": i } as React.CSSProperties}>
            <button
              type="button"
              className={`vehicle${selected === v.alias ? " is-selected" : ""}`}
              aria-pressed={selected === v.alias}
              onClick={() => onSelect(v.alias)}
              data-alias={v.alias}
            >
              <span className="vehicle-head">
                <strong className="alias">{v.alias}</strong>
                <span className={`estado estado-${v.estado}`}><i aria-hidden="true" />{ESTADO[v.estado]}</span>
                {stale && <span className="chip chip-stale">Desactualizado</span>}
                <span className="velocidad">
                  {v.velocidad_kmh.toFixed(1)} <small>km/h</small>
                </span>
              </span>
              {trip ? (
                <span className="trip">
                  <span className="trip-ruta">
                    Viaje {trip.viaje_id} · {trip.corredor} · sentido {trip.sentido}
                  </span>
                  <span className="progress" role="progressbar" aria-label={`Progreso de ${trip.viaje_id}`} aria-valuenow={trip.progreso_pct} aria-valuemin={0} aria-valuemax={100}>
                    <span style={{ width: `${trip.progreso_pct}%` }} />
                  </span>
                  <span className="dato trip-pie">
                    <span>{trip.progreso_pct.toFixed(0)}% · {trip.estado === "en_curso" ? "En curso" : "Finalizado"}</span>
                    <span>{lectura}</span>
                  </span>
                </span>
              ) : (
                <span className="dato trip-pie">
                  <span>{v.viaje_id ? `Viaje ${v.viaje_id}` : "Sin viaje"}</span>
                  <span>{lectura}</span>
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
