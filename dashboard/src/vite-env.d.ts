/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** Estilo MapLibre; "empty" = estilo vacío local (tests sin red) */
  readonly VITE_MAP_STYLE?: string;
  /** Token público de Mapbox (restringido por URL). Sin él el mapa usa MapLibre (CI, Playwright). */
  readonly VITE_MAPBOX_TOKEN?: string;
  /** Alias aceptado del token (mismo nombre que en Vora) */
  readonly NEXT_PUBLIC_MAPBOX_TOKEN?: string;
}
