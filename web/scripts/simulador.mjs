// Genera web/assets/simulador.html desde simulator/fuel-drive.html.
// La landing lo embebe en un iframe: así sus estilos (.iso-*) y su script no
// chocan con los de la página. Aquí solo se cambia el tema a la paleta de
// Certera; el simulador sigue siendo la fuente de verdad.
// Uso: node scripts/simulador.mjs   (desde web/)
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const origen = join(web, "..", "simulator", "fuel-drive.html");
const destino = join(web, "assets", "simulador.html");

// Paleta de web/assets/tokens.css. El iframe no hereda las variables de la
// página, así que se repiten los valores.
const TEMA = `
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* body.iso gana a la hoja del simulador, que va dentro del <body> */
body.iso[data-theme="dark"]{
  --anatomy-page:transparent;--anatomy-card:#0C110E;--anatomy-text:#A4ACA6;--anatomy-strong:#F7F8F2;--anatomy-muted:#6B746E;
  --anatomy-paper:#0C110E;--anatomy-face:#131A16;--anatomy-top:#16201B;
  --anatomy-shade-0:#080C0A;--anatomy-shade-1:#0B100D;--anatomy-shade-2:#0F1512;--anatomy-shade-3:#131A16;
  --anatomy-lit-top:#22302A;--anatomy-lit-shade:#18221D;
  --anatomy-hi:#D9DED9;--anatomy-mid:#6B746E;--anatomy-lo:#2C3631;--anatomy-faint:#1A211E;--anatomy-lit:#F7F8F2;
  --anatomy-halo:#000201;--anatomy-dot:#F7F8F2;
  --anatomy-red:#FF7D8A;--anatomy-green:#D8F36A;--anatomy-blue:#8FB4F0;
  --anatomy-mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;
  --asphalt:#26302B;--paint:#F7F8F2;--smoke:#6B746E;
  --chart-alt:rgba(143,180,240,.12);--chart-ink:#D8F36A;
}
body{background:transparent;font-family:'Inter',system-ui,sans-serif}
.iso-page{width:100%;margin:0}
.iso-figure{margin:0}
.iso-plate{border-radius:10px;background:#000201;box-shadow:0 0 0 1px #1A211E;--anatomy-paper:#000201}
.iso-plate-corner[data-corner="fig"]{display:none}
body .panel{border-radius:8px;background:rgba(12,17,14,.92);box-shadow:0 0 0 1px #2C3631,0 18px 40px -18px #000;backdrop-filter:blur(6px)}
body .p-plot .alt-line{stroke:#8FB4F0}
.iso-legend{margin-top:14px}
body .controls button{border-radius:6px;transition:border-color .18s,color .18s}
body .controls button:hover{border-color:#6B746E;color:#F7F8F2}
body .controls button[aria-pressed="true"]{color:#D8F36A;border-color:rgba(216,243,106,.5);background:rgba(216,243,106,.08)}
body .controls button[data-play],body .controls button[data-play][aria-pressed="true"]{color:#050706;background:#D8F36A;border-color:#D8F36A;font-weight:500}
body .controls button[data-play]:hover{background:#C6E351;color:#050706}
</style>
`;

let html = readFileSync(origen, "utf8");
const cambios = [
  ['<html lang="en">', '<html lang="es">'],
  ["<title>Pendiente y combustible</title>", "<title>Pendiente y combustible · Certera</title>"],
  ['<body class="iso" data-theme="light">', '<body class="iso" data-theme="dark">'],
  ["</head>", `${TEMA}</head>`],
];
for (const [de, a] of cambios) {
  if (!html.includes(de)) throw new Error(`simulator/fuel-drive.html cambió: no encuentro ${de}`);
  html = html.replace(de, a);
}
writeFileSync(destino, html);
console.log(`escrito ${destino} (${html.length} bytes)`);
