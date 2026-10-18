import type { Provenance } from "../api/client";
import { PROCEDENCIA } from "../format";

export function ProvenanceChips({ items }: { items: Provenance[] }) {
  return (
    <ul className="chips" aria-label="Procedencia">
      {items.map((p) => (
        <li key={p} className={`chip chip-${p}`} data-provenance={p}>
          <i aria-hidden="true" />
          {PROCEDENCIA[p]}
        </li>
      ))}
    </ul>
  );
}
