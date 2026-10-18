# Cuadra · Identidad visual y sistema de diseño

> **Versión 1.0** · 17 de octubre de 2026 · The Andes Hackathon
> **Fuente de verdad del código:** [`web/assets/tokens.css`](../../web/assets/tokens.css)
> **Assets:** [`web/assets/brand/`](../../web/assets/brand/)
> **Contexto de producto:** [`docs/gestion-de-facturacion-de-transporte-peru.md`](../gestion-de-facturacion-de-transporte-peru.md)

---

## 0. Cómo usar este documento

| Si eres… | Lee |
|---|---|
| Diseñador / front-end | §3 a §9 completas, §13 para los tokens |
| Back-end / agentes | §2, §5.2 (semántica de estados), §11.3 (glosario) |
| Quien arma el pitch o el deck | §1, §2, §11 |
| Quien escribe copy de UI | §11 completa |

**Regla de oro:** si un color, un tamaño o una palabra no está en este documento, no está en la marca. Antes de inventar, pregunta en el canal del equipo y se agrega acá.

---

## 1. Qué es Cuadra

**Categoría:** Agentic Freight Documentation & Billing Operations.

**Nombre:** Cuadra. Verbo, tercera persona. Es lo que hace el producto y lo que el usuario quiere oír: *cuadró*.

**Línea de marca:** **Que todo cuadre.**

**Propuesta de valor:** Desde el contrato hasta la factura: cada entrega respaldada, cada regla validada, cada liquidación trazable.

**El problema en una frase:** el servicio se ejecutó, la carga llegó y la factura sigue detenida porque falta un sello, un número de orden o una tarifa que nadie puede probar.

**Qué NO somos, y por qué importa para el diseño:**

- No somos un escáner de PODs. No usamos estética de app de scanner ni iconos de cámara como héroe.
- No somos fintech de liquidez. No prometemos dinero ni usamos lenguaje de cashflow como gancho principal.
- No somos un GPS. El mapa no es nuestra imagen central: el expediente lo es.

**Diferenciador visual:** nuestra interfaz muestra la **regla** al lado del **hecho**. Todo lo que afirmamos se puede señalar con el dedo. El diseño existe para que la prueba sea visible.

---

## 2. Principios de marca

Tres principios. Cada uno tiene una consecuencia de diseño obligatoria.

### 2.1. El original no se toca

Se conserva el PDF, la foto o el mensaje tal como llegó. Las correcciones se publican como versiones nuevas, con autor y hora.

> **Consecuencia de diseño:** toda evidencia se muestra con su versión visible (`v1`, `v2`) y su hora. Nunca se reemplaza un archivo en pantalla sin dejar rastro del anterior. El historial no se esconde detrás de un menú de tres puntos.

### 2.2. Dos tiempos, siempre

Cuándo ocurrió el hecho y cuándo se registró son datos distintos. Confundirlos es perder la prueba.

> **Consecuencia de diseño:** todo sello de tiempo en UI muestra los dos tiempos cuando difieren, en mono tabular. Formato: `ocurrió 17 oct 14:22 · registrado 17 oct 19:40`.

### 2.3. Nada se inventa

El sistema señala lo que falta. No genera sellos, firmas ni conformidades que no existieron.

> **Consecuencia de diseño:** el estado *observado* (ámbar) es un estado de primera clase, con el mismo peso visual que *aceptado*. Ningún skeleton, placeholder ni mock en producción puede parecer evidencia real. Los datos de demostración se rotulan como tales.

---

## 3. El símbolo

### 3.1. Concepto

El símbolo es **un expediente visto desde arriba**: un marco de tres lados sobre retícula de 5×5, con el lado derecho abierto —**la puerta**— por donde entra la evidencia. Cuando la puerta se completa, el expediente cuadra.

```
┌───┬───┬───┬───┬───┐   r0  marco (5 módulos)
│ ■ │ ■ │ ■ │ ■ │ ■ │
├───┼───┼───┼───┼───┤
│ ■ │   │   │   │ □ │   r1  marco izq · puerta 1
├───┼───┼───┼───┼───┤
│ ■ │   │ ◆ │   │ □ │   r2  marco izq · SELLO · puerta 2
├───┼───┼───┼───┼───┤
│ ■ │   │   │   │ □ │   r3  marco izq · puerta 3
├───┼───┼───┼───┼───┤
│ ■ │ ■ │ ■ │ ■ │ ■ │   r4  marco (5 módulos)
└───┴───┴───┴───┴───┘

■ marco:   13 módulos macizos, siempre presentes
□ puerta:  3 posiciones, solo se llenan con evidencia aceptada
◆ sello:   módulo central, solo en la marca cerrada
```

### 3.2. Construcción

| Parámetro | Valor |
|---|---|
| Retícula | 5 × 5 |
| Módulo | `u = 1/5 del lado`. Toda medida es múltiplo de `u` |
| Margen del símbolo | `1u` por lado dentro del cuadro del archivo (viewBox de 7u × 7u) |
| Marco | Fila superior, fila inferior y columna izquierda. **13 módulos** |
| Puerta | Columna derecha, filas 1–3. **3 posiciones** |
| Sello | Módulo central (r2, c2). `1u` |
| Separación entre módulos | `1/8 u` desde 48 px de render. Por debajo, módulos macizos sin separación |
| Área de respeto | `1u` libre alrededor del símbolo. Nada entra ahí: ni texto, ni borde, ni otra marca |

Los SVG del repositorio usan `viewBox="0 0 140 140"` con `u = 20`, margen `20`, separación `2.5` y módulo macizo de `15`.

### 3.3. Variantes y cuándo usar cada una

| Variante | Archivo | Uso |
|---|---|---|
| **Abierta** | `cuadra-simbolo-abierto.svg` | **Versión maestra.** Cabecera, firma de correo, documentos. La puerta vacía es el expediente por completar |
| **Abierta sobre claro** | `cuadra-simbolo-abierto-tinta.svg` | La misma, en tinta, para fondos claros y papel |
| **Cerrada** | `cuadra-simbolo-cerrado.svg` | Sello de conformidad. **Solo cuando algo efectivamente cuadró.** Uso restringido: nunca como adorno de portada |
| **Observada** | `cuadra-simbolo-observado.svg` | Dos evidencias aceptadas, una pendiente. Estados e interfaz |
| **Reducción** | `cuadra-simbolo-reduccion.svg` | Por debajo de 48 px: módulos macizos, sin separación |
| **Monocromo** | `cuadra-simbolo-mono.svg` | Soportes que no admiten el acento: todo en tinta, todo en blanco o todo en gris |
| **Favicon** | `cuadra-favicon.svg` | Pestaña del navegador y PWA. 16, 24 o 32 px |

### 3.4. Tamaños mínimos

| Soporte | Mínimo |
|---|---|
| Símbolo solo | **16 px** de alto |
| Símbolo con nombre | **20 px** de alto |
| Marca cerrada (sello) | **48 px** — el módulo central debe ser legible |
| Impresión | **6 mm** de alto |

### 3.5. Qué nunca

- **No rotar ni inclinar.** El cuadrado se lee a escuadra o no se lee.
- **No cerrar la puerta como adorno.** La marca cerrada afirma una conformidad. Usarla sin conformidad real contradice el principio §2.3.
- **No añadir contorno, sombra, degradado, bisel ni brillo.** Los módulos son planos.
- **No cambiar la proporción.** El símbolo es cuadrado. No se estira.
- **No recolorear los módulos del marco.** El marco va en `--cuadra-fg`, en tinta o en gris monocromo. El acento vive solo en la puerta y el sello.
- **No usar sobre fotografía directa.** Solo sobre caja de tinta sólida detrás.
- **No rellenar la puerta parcialmente por estética.** En interfaz, la puerta refleja el estado real del expediente.

---

## 4. Logotipo y lockups

### 4.1. El nombre

**CUADRA** en Archivo Black, mayúsculas, `letter-spacing: .02em`. Nunca "CuADRA", "cuadra®" ni con punto final.

### 4.2. Lockups

| Lockup | Construcción | Uso |
|---|---|---|
| **Horizontal** (principal) | Símbolo + nombre a la derecha. Separación `2u`. Altura de mayúsculas = `2u`. Alineación al centro óptico vertical | Cabecera web, nav, presentaciones |
| **Vertical** | Símbolo arriba, nombre abajo centrado. Separación `1.5u` | Espacios estrechos, avatar, sticker |
| **Sobre blanco** | Variante en tinta, mismas proporciones | Documentos al cliente, PDF, impresión |
| **Símbolo solo** | Sin nombre | Favicon, app móvil, cuando el nombre ya aparece cerca |

### 4.3. Pendiente de producción

Los lockups de este repositorio se componen **en código**: símbolo SVG más texto en Archivo Black. Para entregables fuera del navegador —imprenta, merchandising, materiales de terceros— hay que **vectorizar el texto** en Figma o Illustrator y versionar el `.svg` resultante acá. No enviar a imprenta un SVG con el texto como fuente: si la imprenta no tiene Archivo Black, el logo se rompe sin avisar.

---

## 5. Color

### 5.1. Paleta

Cuadra vive sobre tinta. La tinta es el papel de este producto.

| Token | Hex | Nombre | Rol |
|---|---|---|---|
| `--cuadra-tinta` | `#07090F` | Tinta | Fondo base de todo |
| `--cuadra-tinta-2` | `#0E121B` | Tinta elevada | Tarjeta, panel, superficie |
| `--cuadra-tinta-3` | `#141926` | Tinta sobre tinta | Superficie dentro de superficie |
| `--cuadra-tinta-pozo` | `#04060B` | Pozo | Huecos: visor de documento, stage, video |
| `--cuadra-linea` | `#222A3B` | Línea | Retícula visible, borde de 1 px |
| `--cuadra-fg` | `#EDF1F8` | Texto | Texto principal, módulos del marco |
| `--cuadra-fg-dim` | `#848FA6` | Texto atenuado | Párrafo secundario, etiquetas |
| `--cuadra-fg-mute` | `#5B6578` | Texto apagado | Deshabilitado, metadato terciario |
| **`--cuadra-sello`** | **`#00D8B4`** | **Verde sello** | **Acento único.** Aceptado, cuadró |
| `--cuadra-observa` | `#F5A524` | Ámbar subsanación | Falta una pieza concreta |
| `--cuadra-rechazo` | `#E5484D` | Rojo evidencia ausente | Lo exigido no existe |

El gris `#848FA6` tiene sesgo azul-verdoso hacia el acento. No es un gris neutro: es el gris de esta marca.

### 5.2. El color es un veredicto

Esta es la regla más importante del sistema. **Ámbar y rojo son estados, no decoración.**

| Color | Significa exactamente | Nunca significa |
|---|---|---|
| Verde sello | Una persona o una regla **aceptó** esto. Hay un aprobador identificado y una hora | "Bonito", "destacado", "nuestro color" |
| Ámbar | Falta **una pieza concreta** y se sabe cuál. Hay una acción posible para subsanar | "Advertencia genérica", "en progreso" |
| Rojo | Lo exigido **no existe**. No se puede subsanar sin una decisión fuera del sistema | "Error de red", "botón de borrar", "urgente" |

Corolarios:

- Ámbar y rojo **no aparecen en marketing** salvo para mostrar un estado real de producto.
- El verde sello **no se usa como color de párrafo**. Subraya, no decora.
- Si necesitas destacar algo que no es un estado, usa jerarquía tipográfica o la línea de la retícula, no color.

### 5.3. Proporción

```
Tinta         ████████████████████████████████████████  80
Superficies   ███████                                    14
Acento        ███                                         6
```

El verde sello nunca cubre áreas grandes. Un botón primario, un borde superior de KPI, una etiqueta, la puerta del símbolo. Eso es todo.

### 5.4. Contraste y accesibilidad

| Combinación | Veredicto |
|---|---|
| `--cuadra-fg` sobre `--cuadra-tinta` | Texto de cualquier tamaño |
| `--cuadra-fg-dim` sobre `--cuadra-tinta` | Texto normal, OK |
| `--cuadra-fg-mute` sobre `--cuadra-tinta` | **Solo** ≥ 18.66 px bold o ≥ 24 px, o elementos no textuales |
| `--cuadra-sello` sobre `--cuadra-tinta` | OK para texto y para iconografía |
| `--cuadra-tinta` sobre `--cuadra-sello` | **Botón primario: texto tinta sobre verde.** Nunca texto blanco sobre verde |
| `--cuadra-observa` sobre `--cuadra-tinta` | OK |
| `--cuadra-rechazo` sobre `--cuadra-tinta` | Texto normal OK. Para texto pequeño crítico, acompañar con icono o palabra |

Los ratios exactos están pendientes de medición con una herramienta de contraste; las combinaciones de arriba se eligieron para superar AA y la tabla registra el uso permitido, no el número.

Además: **el estado nunca se comunica solo por color.** Todo chip de estado lleva su palabra (`Aceptado`, `Observado`, `Sin evidencia`). Un daltónico tiene que poder liquidar un viaje.

### 5.5. Soporte claro

Para documentos impresos y PDF al cliente existe la clase `.cuadra-papel` en `tokens.css`, que invierte la paleta de forma controlada y **oscurece el acento** a `#00806E` para que mantenga contraste sobre blanco. No se usa un tema claro del navegador: Cuadra en pantalla es una marca de tinta, con un solo mundo visual.

---

## 6. Tipografía

### 6.1. Familias

| Rol | Familia | Peso | Por qué |
|---|---|---|---|
| **Display** | Archivo Black | 400 (único) | Grotesca condensada y maciza. Afirma. Es un sello tipográfico, no un titular elegante |
| **Texto** | Archivo | 400, 500, 600, 700 | Misma familia, misma estructura. Legible a 13 px en cabina |
| **Dato** | IBM Plex Mono | 400, 500, 600 | Series, RUC, placas, montos. Tabular por defecto |

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=Archivo+Black&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
```

Las tres son **SIL Open Font License 1.1**: libres para uso comercial, incrustación y distribución. Se pueden autoalojar si el proyecto lo necesita.

**Fallbacks declarados** (obligatorios; una fuente que no carga en silencio es un bug):

```css
--cuadra-display: 'Archivo Black', Impact, 'Haettenschweiler', system-ui, sans-serif;
--cuadra-body:    'Archivo', system-ui, -apple-system, 'Segoe UI', sans-serif;
--cuadra-mono:    'IBM Plex Mono', ui-monospace, 'SFMono-Regular', Consolas, monospace;
```

### 6.2. Escala

| Token | Tamaño | Familia y ajustes | Uso |
|---|---|---|---|
| `--cuadra-t-mega` | `clamp(46px, 11vw, 148px)` | display · `line-height:.84` · `-.045em` · UPPER | Un solo uso por página: el titular del hero |
| `--cuadra-t-h1` | `clamp(34px, 6.4vw, 72px)` | display · `.90` · `-.038em` · UPPER | Título de sección |
| `--cuadra-t-h2` | `clamp(26px, 4vw, 40px)` | display · `.95` · `-.03em` · UPPER | Subsección, cifra grande |
| `--cuadra-t-h3` | `20px` | body 700 · `1.25` · `-.012em` | Título de tarjeta |
| `--cuadra-t-lede` | `clamp(16px, 1.7vw, 19px)` | body 400 · `1.55` · máx `58ch` | Párrafo de entrada |
| `--cuadra-t-body` | `16px` | body 400 · `1.6` · máx `65ch` | Texto corrido |
| `--cuadra-t-dato` | `17px` | mono 500 · `1.4` · tabular | OS, GRE, placa, monto |
| `--cuadra-t-micro` | `13px` | body 400 · `1.5` | Descripción de tarjeta, pie |
| `--cuadra-t-label` | `11px` | mono 500 · `.22em` · UPPER | Eyebrow, etiqueta de estado, metadato |

### 6.3. Reglas

1. **Toda cifra lleva `font-variant-numeric: tabular-nums`.** En este producto las columnas tienen que cuadrar también a la vista.
2. **Los montos llevan moneda y separador peruano:** `S/ 12 480,00`. Espacio fino como separador de miles, coma decimal.
3. **Titulares en display van en mayúsculas.** Archivo Black en minúsculas pierde su carácter de sello.
4. **`text-wrap: balance` en todo h1/h2/h3.** Un titular con una palabra huérfana en la última línea es un error de oficio.
5. **Una sola `--cuadra-t-mega` por página.** Si hay dos, ninguna es el titular.
6. **Identificadores siempre en mono**, incluso dentro de un párrafo: la `OS-1042` se reconoce por su forma antes de leerla.
7. **Las etiquetas en mayúsculas llevan tracking.** Sin `.22em` se ven apretadas y amateur.

### 6.4. Muestra canónica

```
Display   DEL CONTRATO A LA FACTURA
Titular   Expediente observado: falta número de orden
Texto     Una cotización aceptada sin fijar qué se cobra por esperas
          o entregas fallidas genera diferencias semanas después.
Dato      OS-1042 · GRE T001-0009318 · B7K-914 · S/ 12 480,00
Etiqueta  ACEPTADO · 17 OCT 2026 · 14:22 · V2
```

---

## 7. Retícula, espacio y forma

### 7.1. Espacio

La escala de espacio es la misma retícula del símbolo: `u = 8px`, y todo es múltiplo.

`8 · 16 · 24 · 32 · 48 · 64 · 88`

| Token | Uso |
|---|---|
| `--cuadra-s-1` (8) | Separación dentro de un componente |
| `--cuadra-s-2` (16) | Padding de chip, gap de lista, gutter mínimo |
| `--cuadra-s-3` (24) | Padding de tarjeta |
| `--cuadra-s-4` (32) | Separación entre bloques de una sección |
| `--cuadra-s-6` (48) | Separación entre grupos |
| `--cuadra-s-8` (64) | Aire interno de sección |
| `--cuadra-s-11` (88) | `padding-block` entre secciones |

Se maqueta con `flex`/`grid` y `gap`. **No se usan márgenes por elemento**: colapsan o se duplican sin avisar.

### 7.2. Contenedor

`max-width: 1240px`, centrado, con gutter lateral:

```css
padding-left:  max(16px, env(safe-area-inset-left, 0px));
padding-right: max(16px, env(safe-area-inset-right, 0px));
```

Cuando una banda de color ocupa todo el ancho, el gutter va en su wrapper interno, nunca en la banda.

### 7.3. Forma: `border-radius: 0`

**Sin excepciones en toda la marca.** El cuadrado se lee a escuadra o no se lee. Botones, tarjetas, chips, inputs, avatares, modales: ángulo recto. Esto es lo que más distingue a Cuadra de cualquier SaaS genérico, y lo primero que alguien romperá por costumbre. No lo rompas.

El único redondeo admitido es el del propio navegador en controles nativos que no estilizamos.

### 7.4. Borde y elevación

- La jerarquía se construye con **línea de 1 px** (`--cuadra-linea`), no con sombra.
- **No hay sombras** en el sistema. Una tarjeta se separa del fondo por su superficie (`--cuadra-tinta-2`) y su borde.
- El hover de una superficie interactiva cambia el **color del borde** a `--cuadra-sello` y levanta `translateY(-3px)`. Nada más.

---

## 8. Movimiento

### 8.1. La idea

La animación cuenta el producto entero: **lo disperso se asienta**. Los módulos empiezan fuera de la retícula —como la evidencia hoy: fotos, chats, guías, correos— y se asientan hasta que la puerta cierra.

**Nada se desliza en continuo: cada módulo llega a su casilla y se queda.**

### 8.2. Los cinco estados

| Estado | Lectura | Especificación |
|---|---|---|
| `disperso` | Evidencia sin vínculo con la orden ni con la regla | Deriva, bucle continuo, amplitud `.55 ± .25` |
| `alineando` | Cada evidencia se enlaza con su cláusula y su línea | Asentado 2 800 ms, salida cúbica |
| `observado` | Falta una pieza concreta y la puerta no cierra | Parpadeo 900 ms en la posición libre |
| `cuadrado` | Puerta cerrada, expediente conforme | Estático |
| `facturado` | Listo para facturar | Sello central, pulso 1 800 ms |

### 8.3. Reglas

1. **La puerta nunca se cierra sola en una animación decorativa.** Si un módulo entra, es porque hay una evidencia detrás.
2. Duraciones: `180ms` para respuesta a un clic, `380ms` para una transición de estado, `2800ms` para la secuencia narrativa completa. Nada intermedio.
3. Easing único: `cubic-bezier(.16,.84,.26,1)` — llega rápido y se asienta.
4. `@media (prefers-reduced-motion: reduce)` apaga **toda** animación y transición, y los estados animados se muestran en su fotograma final.
5. Sin parallax, sin scroll-jacking, sin texto que aparece al entrar en viewport. **La página está completa en reposo**: lo que hay que leer se lee sin scrollear ni esperar.

---

## 9. Componentes

Nomenclatura y anatomía. Los nombres de clase son los del repositorio.

### 9.1. Chip de estado · `.cq-estado`

El componente más importante del producto.

```
┌────────────────────┐
│ ■ ACEPTADO         │   cuadrado de 10px del color + palabra en mono 11 UPPER
└────────────────────┘   borde de 1px, padding 8/13, sin radio
```

Siempre lleva palabra. Variantes: `.es-aceptado` (sello), `.es-observado` (ámbar), `.es-ausente` (rechazo), `.es-pendiente` (fg-dim).

### 9.2. Tarjeta · `.cq-tarjeta`

Superficie `--cuadra-tinta-2`, borde `--cuadra-linea`, padding `24px`, sin radio. Orden interno fijo: **eyebrow → título → texto → metadato**. El metadato siempre al pie, en mono 11.

### 9.3. Fila de evidencia · `.cq-evidencia`

Cuadrado de estado · nombre de la evidencia · regla que la exige · versión y hora. La **regla citada es obligatoria**: una evidencia observada sin la cláusula que la exige es una acusación sin sustento.

### 9.4. Veredicto · `.cq-veredicto`

Display 15 px UPPER, color del estado. Texto corto y literal: `2 requisitos incumplidos · no cuadra`, `Cuadra · listo para facturar`. Nunca un porcentaje solo.

### 9.5. Cifra · `.cq-kpi`

Borde superior de 3 px del color del estado, cifra en display con `tabular-nums`, etiqueta en mono 11 debajo. La etiqueta dice **cómo se mide**, no solo qué es.

### 9.6. Eslabón de cadena · `.cq-eslabon`

Número en verde sello más nombre de la fase. Los diez eslabones en orden: Cotización · Acuerdo y tarifario · Orden de servicio · Despacho y guías · Ejecución del viaje · Entrega y POD · Conformidad · Liquidación · Factura · Cobro. **El número es información real** (la fase 6 es la fase 6), no decoración.

### 9.7. Botón · `.cq-btn`

| Variante | Fondo | Texto | Uso |
|---|---|---|---|
| Primaria | `--cuadra-sello` | `--cuadra-sobre-acento` | **Una por vista.** La acción que hace avanzar el expediente |
| Secundaria | transparente, borde `--cuadra-linea` | `--cuadra-fg` | Todo lo demás |
| Fantasma | transparente, sin borde | `--cuadra-fg-dim` | Acción terciaria |

Texto en mono 11 UPPER con tracking. El botón dice exactamente qué pasa: `Enviar requerimiento`, no `Continuar`. Foco visible obligatorio: `outline: 2px solid var(--cuadra-sello); outline-offset: 2px`.

### 9.8. Sello de conformidad en documento · `.cq-sello-doc`

Marca cerrada + "EXPEDIENTE CONFORME" + línea de datos en mono. **Solo se imprime cuando existe una aceptación registrada con aprobador identificado.** Nunca como adorno de portada.

---

## 10. Iconografía e imagen

### 10.1. Iconos

- Trazo de 1,5 px, extremos rectos, sin redondeo, retícula de 24 px.
- Geometría derivada del cuadrado: el icono de documento es un rectángulo, no una hoja con la esquina doblada.
- Color: `--cuadra-fg-dim` en reposo, `--cuadra-fg` activo. El acento solo cuando el icono comunica estado.
- **El cuadrado de 10 px de estado no es un icono**, es el componente `.cq-estado`. No lo reemplaces por un check ni por un emoji.
- Sin emoji en UI ni como marcador de sección.

### 10.2. Fotografía

Cuando haya foto —cabina, patio de maniobras, mesa de recepción, un sello real sobre papel— se usa así:

- Virada hacia la tinta: alto contraste, sombras profundas, sin filtro de color cálido.
- El símbolo nunca va directo sobre la imagen: siempre con caja de tinta sólida detrás.
- Texto sobre foto solo con velo de tinta al 70 % o más.
- Nada de stock de ejecutivos sonriendo con tablet. Si no hay foto real del contexto peruano, es mejor una superficie de tinta con tipografía.

### 10.3. Gráficos generativos

Los campos de puntos, las retículas animadas y el símbolo en movimiento se dibujan en **Canvas**, no con SVG de rutas largas. Es lo que ya hace la landing.

---

## 11. Voz y tono

### 11.1. Cómo suena Cuadra

**Preciso, literal, sin adornos.** La voz de alguien que ha visto el expediente y puede señalar exactamente qué falta. Nunca vendedor, nunca alarmista, nunca condescendiente con el conductor ni con el administrativo.

| Sí | No |
|---|---|
| `Falta el número de orden en la guía. El anexo de la sede A exige consignar OS-1042 en el documento de recepción.` | `¡Ups! Parece que hay un problemita con tu documento` |
| `Preliquidación por tarifa acordada: S/ 12 480,00. Lista para facturar.` | `¡Desbloquea tu liquidez al instante!` |
| `2 requisitos de la política de POD vigente para esta sede no se cumplen.` | `Documento inválido` |
| `La entrega física ocurrió. El expediente todavía no es aceptable.` | `Error en la validación` |

### 11.2. Reglas de escritura

1. **Voz activa.** El control dice qué pasa: `Enviar requerimiento`, y después el aviso dice `Requerimiento enviado`.
2. **Un error explica qué pasó y cómo se arregla.** Sin disculpas, sin vaguedad.
3. **Nombra las cosas como las nombra el usuario**, no como está construido el sistema: *expediente*, no *payload*; *conformidad*, no *approval flag*.
4. **Nunca prometer dinero.** Decimos "listo para facturar" y "valor entregado sin facturar". No decimos "cobra hoy" ni "liquidez inmediata": una aprobación más rápida adelanta la facturación, no cambia los días de crédito ni la conducta de pago del cliente.
5. **Toda cifra de impacto lleva su definición al lado.** Si no sabemos cómo se mide, no la publicamos.
6. **Los datos de demostración se rotulan.** `Contrato y datos de demostración.`
7. Sin signos de exclamación en UI. Sin "simplemente", "solo tienes que", "potente", "revolucionario", "sin esfuerzo".
8. Español peruano de negocio. `S/`, `RUC`, `GRE`, `OS`, `OC`, `SUNAT`, `sede`, `conductor`, `estiba`.

### 11.3. Glosario: usar estas palabras y no otras

| Decimos | No decimos | Por qué |
|---|---|---|
| **Expediente** | Carpeta, archivo, caso | El POD es un expediente de evidencias, no un PDF |
| **Evidencia** | Documento, adjunto | Lo que importa es su valor probatorio |
| **Conformidad** | Aprobación, visto bueno | Tiene un aprobador identificado y una hora |
| **Observado** | Rechazado, inválido | Falta una pieza concreta y se puede subsanar |
| **Subsanación** | Corrección, fix | Es el término que usa el administrativo |
| **Regla aplicable** | Política, config | Está en una cláusula, con versión y vigencia |
| **Listo para facturar** | Facturado, cobrado | Facturación emite; nosotros preparamos |
| **Preliquidación** | Cálculo, total | Es una propuesta sujeta a aprobación |
| **Entrega física** | Entrega | Distinta de la aceptación del expediente |
| **Hora del hecho / hora de registro** | Fecha | Dos tiempos, siempre (§2.2) |

### 11.4. Los tres hitos que nunca se confunden

Escribir "entregado" cuando queremos decir "aceptado" es el peor error de copy posible en este producto.

1. **Entrega física** de la mercancía.
2. **Aceptación del expediente** POD o conformidad comercial del servicio.
3. **Conformidad de la factura electrónica** para fines de factura negociable.

No son lo mismo ni ocurren juntos.

### 11.5. Límites que se declaran, no se esconden

Cada agente publica en la interfaz qué **no** hace. Es diferenciador, no debilidad:

> *POD Validation — Compara, no completa. Límite: no genera evidencia.*

---

## 12. Aplicaciones

La marca vive en tres sitios. En los tres, **el símbolo informa un estado antes que una identidad.**

| Soporte | Qué cambia |
|---|---|
| **Expediente en pantalla** (web, panel admin) | Tinta, densidad alta, mono para todo dato. El símbolo del nav refleja el estado del expediente abierto |
| **App del conductor** (cabina, una mano, sol directo) | Tipografía un paso más grande, áreas de toque de 48 px mínimo, contraste máximo. Sin estados ambiguos: lo que falta se dice con palabra y foto de ejemplo |
| **Documentos al cliente** (PDF, impreso) | `.cuadra-papel`. Marca en tinta sobre blanco. Sello de conformidad solo si existe aceptación registrada |

---

## 13. Estructura del repositorio

```
npm-devs/
├── docs/
│   ├── brand/
│   │   └── IDENTIDAD-VISUAL.md          ← este documento
│   ├── gestion-de-facturacion-de-transporte-peru.md
│   ├── rubrica-evaluacion.md
│   └── research/ · feedback/
└── web/
    ├── index.html                        ← landing
    └── assets/
        ├── tokens.css                    ← única fuente de verdad de color y tipo
        ├── brand/
        │   ├── cuadra-simbolo-abierto.svg
        │   ├── cuadra-simbolo-abierto-tinta.svg
        │   ├── cuadra-simbolo-cerrado.svg
        │   ├── cuadra-simbolo-observado.svg
        │   ├── cuadra-simbolo-reduccion.svg
        │   ├── cuadra-simbolo-mono.svg
        │   └── cuadra-favicon.svg
        └── media/                        ← video e imagen del hero (ver §14)
```

---

## 14. Huecos de contenido en la landing

La landing tiene dos espacios reservados para material que el equipo va a producir. Están marcados en `web/index.html` con el comentario `<!-- HUECO -->`.

### 14.1. Imagen del hero · `#hero-imagen`

- **Relación:** 4:5 vertical. Ocupa la columna derecha del hero.
- **Qué debe mostrar:** el contexto real. Un sello sobre papel, una mesa de recepción, la guía firmada, la cabina. No stock.
- **Tratamiento:** virada a tinta, alto contraste (§10.2).
- **Cómo reemplazar:** poner el archivo en `web/assets/media/hero.webp` y descomentar el `<img>` que está dentro de `#hero-imagen`. El placeholder actual es la retícula animada en Canvas y funciona como fallback definitivo si no llega la imagen.
- **Peso:** máximo 400 KB, formato `.webp` preferido.

### 14.2. Video · `#video`

- **Relación:** 16:9.
- **Duración objetivo:** 90 segundos. Guion sugerido: expediente detenido → el agente señala la cláusula → subsanación → puerta cerrada → listo para facturar.
- **Cómo reemplazar:** poner `web/assets/media/demo.mp4` y `demo-poster.webp`, y descomentar el bloque `<video controls poster="...">` dentro de `#video`.
- **Importante:** si la landing se publica como Artifact de Claude, **no puede embeber YouTube ni Vimeo**: los iframes externos están bloqueados. En el repositorio desplegado sí se puede. Para el Artifact, usar `<video>` con archivo propio, o dejar el poster con un enlace que abra el video fuera.
- **Accesibilidad:** subtítulos `.vtt` obligatorios. El video no es la única fuente de la información: la demo interactiva de la página cuenta la misma historia sin audio.

---

## 15. Checklist antes de publicar cualquier pantalla

- [ ] Todos los colores salen de `tokens.css`. Ningún hex literal en el componente.
- [ ] `border-radius: 0` en todo. Sin sombras.
- [ ] Toda cifra con `tabular-nums`. Montos con `S/` y coma decimal.
- [ ] Todo identificador (`OS-`, `GRE`, placa) en mono.
- [ ] Todo chip de estado lleva su palabra, no solo color.
- [ ] Toda evidencia observada muestra la regla que la exige.
- [ ] Sellos de tiempo: hora del hecho y hora de registro cuando difieren.
- [ ] Datos de demostración rotulados como tales.
- [ ] Ningún copy promete dinero cobrado.
- [ ] Una sola `--cuadra-t-mega` y un solo botón primario por vista.
- [ ] Foco de teclado visible en todo elemento interactivo.
- [ ] `prefers-reduced-motion` apaga la animación y deja el fotograma final.
- [ ] A 400 px de ancho: sin scroll horizontal, gutter de 16 px, columnas apiladas.
- [ ] La página está completa en reposo: nada queda en `opacity: 0` esperando scroll.

---

## 16. Anti-patrones: lo que delata un diseño genérico

Si tu pantalla tiene alguno de estos, no es Cuadra:

1. Esquinas redondeadas.
2. Degradado violeta-azul, o cualquier degradado como fondo de sección.
3. Sombra suave en tarjetas.
4. Emoji como marcador de sección.
5. Todo centrado.
6. Inter o Space Grotesk como tipografía.
7. Hero de `100vh` que empuja el contenido fuera de la primera vista.
8. Tres tarjetas idénticas con icono circular arriba.
9. Verde sello usado como "nuestro color" sobre áreas grandes.
10. Un contador de "+1 000 empresas confían en nosotros" que no podemos sustentar.
11. Texto que aparece con fade al entrar en viewport.
12. Un mapa con pines como imagen central.

---

## 17. Pendientes de esta versión

| Pendiente | Responsable | Notas |
|---|---|---|
| Vectorizar el lockup para imprenta | Diseño | §4.3 |
| Imagen y video del hero | Equipo | §14 |
| Medir los ratios de contraste exactos y anotarlos en §5.4 | Diseño | Cualquier verificador de WCAG |
| Tokens para el panel de admin: densidad, tabla densa, formularios | Front-end | Extensión de §9, no reemplazo |
| Iconografía completa, set de 24 | Diseño | §10.1 define las reglas, falta el set |
| Revisión de contraste en la app del conductor bajo sol directo | Diseño | §12 |
| Versión en inglés del glosario, si el jurado lo pide | Producto | §11.3 |

---

**Cuadra · identidad visual v1.0 · octubre 2026.** Contratos, órdenes y montos usados como ejemplo en este documento son de demostración. Este documento describe un sistema de diseño; no constituye asesoría legal ni tributaria.
