// Genera los íconos y la imagen para compartir en redes desde el símbolo de marca.
//   assets/brand/favicon-32.png, favicon-192.png, favicon-512.png
//   assets/brand/apple-touch-icon.png (180)   favicon.ico (32, en la raíz)
//   assets/og-certera.png (1200x630, la tarjeta de WhatsApp, LinkedIn, X...)
// Uso: node scripts/imagenes.mjs   (desde web/; usa el Chromium de Playwright)
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const brand = join(web, "assets", "brand");
const favicon = readFileSync(join(brand, "certera-favicon.svg"), "utf8");
const simbolo = readFileSync(join(brand, "certera-simbolo.svg"), "utf8");

const browser = await chromium.launch();
const page = await browser.newPage();

async function png(html, width, height, destino) {
  await page.setViewportSize({ width, height });
  await page.setContent(html, { waitUntil: "networkidle" });
  const buf = await page.screenshot({ omitBackground: true });
  writeFileSync(destino, buf);
  return buf;
}

const icono = (px) =>
  `<style>html,body{margin:0;background:transparent}svg{display:block;width:${px}px;height:${px}px}</style>${favicon}`;

let png32;
for (const [px, nombre] of [[32, "favicon-32.png"], [180, "apple-touch-icon.png"], [192, "favicon-192.png"], [512, "favicon-512.png"]]) {
  const buf = await png(icono(px), px, px, join(brand, nombre));
  if (px === 32) png32 = buf;
}

// favicon.ico con una sola imagen PNG de 32x32 (formato ICO admite PNG embebido).
const cabeza = Buffer.alloc(22);
cabeza.writeUInt16LE(0, 0); cabeza.writeUInt16LE(1, 2); cabeza.writeUInt16LE(1, 4);
cabeza.writeUInt8(32, 6); cabeza.writeUInt8(32, 7); cabeza.writeUInt8(0, 8); cabeza.writeUInt8(0, 9);
cabeza.writeUInt16LE(1, 10); cabeza.writeUInt16LE(32, 12);
cabeza.writeUInt32LE(png32.length, 14); cabeza.writeUInt32LE(22, 18);
writeFileSync(join(web, "favicon.ico"), Buffer.concat([cabeza, png32]));

// Perfil de altura estilizado Chosica → Ticlio → La Oroya, el mismo escenario de la landing.
const PERFIL = [[0, 860], [20, 1450], [40, 2300], [60, 3150], [75, 3700], [90, 4400], [100, 4818], [112, 4300], [125, 3745]];
const W = 1200, H = 630, x0 = 660, x1 = 1140, y0 = 520, y1 = 150;
const px = (km) => x0 + (km / 125) * (x1 - x0);
const py = (m) => y0 - ((m - 800) / (4900 - 800)) * (y0 - y1);
const linea = PERFIL.map(([k, m], i) => `${i ? "L" : "M"}${px(k).toFixed(1)} ${py(m).toFixed(1)}`).join(" ");
const area = `${linea} L${x1} ${y0} L${x0} ${y0} Z`;

const og = `<!doctype html><html><head>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Inter:wght@400;500&family=IBM+Plex+Mono:wght@500&display=swap">
<style>
*{box-sizing:border-box}html,body{margin:0}
body{width:${W}px;height:${H}px;background:#050706;color:#F7F8F2;font-family:Inter,sans-serif;position:relative;overflow:hidden}
.reticula{position:absolute;inset:0;background-image:linear-gradient(#121815 1px,transparent 1px),linear-gradient(90deg,#121815 1px,transparent 1px);background-size:40px 40px;mask-image:radial-gradient(ellipse at 75% 55%,#000 20%,transparent 75%)}
.halo{position:absolute;width:720px;height:720px;right:-160px;top:-120px;background:radial-gradient(circle,rgba(216,243,106,.13),transparent 62%)}
.texto{position:absolute;left:72px;top:70px;width:520px}
.marca{display:flex;align-items:center;gap:16px;font-family:Manrope;font-weight:800;font-size:34px;letter-spacing:-.02em}
.marca svg{width:52px;height:52px}
.eyebrow{margin-top:70px;font-family:'IBM Plex Mono';font-size:15px;letter-spacing:.2em;text-transform:uppercase;color:#D8F36A}
h1{margin:18px 0 0;font-family:Manrope;font-weight:800;font-size:58px;line-height:1.02;letter-spacing:-.035em}
p{margin:24px 0 0;font-size:22px;line-height:1.45;color:#A4ACA6}
svg.perfil{position:absolute;left:0;top:0}
.rot{font-family:'IBM Plex Mono';font-size:14px;letter-spacing:.08em;fill:#6B746E}
</style></head><body>
<div class="reticula"></div><div class="halo"></div>
<svg class="perfil" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8FB4F0" stop-opacity=".28"/><stop offset="1" stop-color="#8FB4F0" stop-opacity="0"/></linearGradient></defs>
  <path d="${area}" fill="url(#g)"/>
  <path d="${linea}" fill="none" stroke="#8FB4F0" stroke-width="3" stroke-linejoin="round"/>
  <line x1="${px(100)}" y1="${py(4818) - 14}" x2="${px(100)}" y2="${y0}" stroke="#2C3631" stroke-dasharray="4 5"/>
  <circle cx="${px(100)}" cy="${py(4818)}" r="7" fill="#D8F36A"/>
  <circle cx="${px(100)}" cy="${py(4818)}" r="16" fill="none" stroke="#D8F36A" stroke-opacity=".35" stroke-width="2"/>
  <text class="rot" x="${px(100) - 6}" y="${py(4818) - 30}" text-anchor="end" fill="#F7F8F2">TICLIO · 4 818 msnm</text>
  <text class="rot" x="${x0}" y="${y0 + 34}">CHOSICA 860</text>
  <text class="rot" x="${x1}" y="${y0 + 34}" text-anchor="end">LA OROYA</text>
</svg>
<div class="texto">
  <div class="marca">${simbolo.replace(/<!--[\s\S]*?-->/g, "")}Certera</div>
  <div class="eyebrow">Telemetría · pendiente · flota</div>
  <h1>Señales claras.<br>Decisiones certeras.</h1>
  <p>Cruza la telemetría del camión con la pendiente de la ruta y avisa antes de que se quede sin diésel en los Andes.</p>
</div>
</body></html>`;
await png(og, W, H, join(web, "assets", "og-certera.png"));

await browser.close();
console.log("íconos e imagen para redes generados");
