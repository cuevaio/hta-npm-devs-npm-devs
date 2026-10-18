/**
 * Marcador de tractocamión visto desde arriba, apuntando al norte; el mapa lo gira con --rumbo.
 * El color de la cabina y la franja del tráiler salen de data-estado (styles.css), así un cambio de
 * estado no rehace el SVG. viewBox centrado en el camión para que gire sobre su centro.
 */
export function truckMarkup(alias: string): string {
  const haz = `haz-${alias.replace(/[^\w-]/g, "")}`;
  const nervios = [32, 38, 44, 50, 56, 62, 68].map((y) => `<line class="nervio" x1="13.5" y1="${y}" x2="26.5" y2="${y}"/>`).join("");
  return `
<span class="halo" aria-hidden="true"></span>
<span class="camion-giro" aria-hidden="true">
  <svg class="camion" viewBox="0 -24 40 128" focusable="false">
    <defs>
      <linearGradient id="${haz}" x1="0" y1="1" x2="0" y2="0">
        <stop offset="0" stop-color="#F7F8E0" stop-opacity=".55"/>
        <stop offset="1" stop-color="#F7F8E0" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path class="haz" d="M13.5 5 L26.5 5 L34 -22 L6 -22 Z" fill="url(#${haz})"/>
    <rect class="sombra" x="10.5" y="7" width="19" height="69" rx="4"/>
    <rect class="trailer" x="12" y="26" width="16" height="48" rx="2"/>
    ${nervios}
    <rect class="franja" x="19.2" y="28" width="1.6" height="44" rx=".8"/>
    <rect class="enganche" x="17.5" y="22" width="5" height="5" rx="1"/>
    <rect class="espejo" x="10.2" y="10.5" width="2.6" height="1.6" rx=".6"/>
    <rect class="espejo" x="27.2" y="10.5" width="2.6" height="1.6" rx=".6"/>
    <rect class="cabina" x="12.5" y="6" width="15" height="17" rx="3.6"/>
    <rect class="parabrisas" x="14" y="8.2" width="12" height="3.6" rx="1.4"/>
    <rect class="techo" x="15" y="14" width="10" height="7" rx="1.6"/>
    <rect class="faro" x="13.6" y="5.4" width="3" height="1.3" rx=".6"/>
    <rect class="faro" x="23.4" y="5.4" width="3" height="1.3" rx=".6"/>
    <rect class="intermitente" x="12.4" y="19.4" width="1.8" height="2.4" rx=".6"/>
    <rect class="intermitente" x="25.8" y="19.4" width="1.8" height="2.4" rx=".6"/>
    <rect class="intermitente" x="12.2" y="71.6" width="1.8" height="2.4" rx=".6"/>
    <rect class="intermitente" x="26" y="71.6" width="1.8" height="2.4" rx=".6"/>
    <rect class="freno" x="14.6" y="73" width="3.2" height="1.4" rx=".6"/>
    <rect class="freno" x="22.2" y="73" width="3.2" height="1.4" rx=".6"/>
  </svg>
</span>
<span class="tag"><b></b><span class="tag-dato"></span></span>`;
}

/** Rumbo en grados (0 = norte, horario) de `a` a `b`, en lon/lat. */
export function bearing(a: [number, number], b: [number, number]): number {
  const rad = Math.PI / 180;
  const dLon = (b[0] - a[0]) * rad;
  const y = Math.sin(dLon) * Math.cos(b[1] * rad);
  const x = Math.cos(a[1] * rad) * Math.sin(b[1] * rad) - Math.sin(a[1] * rad) * Math.cos(b[1] * rad) * Math.cos(dLon);
  return (Math.atan2(y, x) / rad + 360) % 360;
}

/** Ángulo acumulado que llega a `target` por el camino corto (de 350° a 10° gira 20°, no 340°). */
export function unwrap(current: number, target: number): number {
  const delta = ((((target - current) % 360) + 540) % 360) - 180;
  return current + delta;
}
