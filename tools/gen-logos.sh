#!/bin/sh
# Genera el sistema de símbolo Cuadra desde la retícula 5x5 del manual de marca.
# u = 20, margen = 1u, separación = 1/8 u = 2.5 -> módulo macizo 15x15 en viewBox 140.
OUT="$1"
SELLO="#00D8B4"
AMBAR="#F5A524"
FG="#EDF1F8"
TINTA="#07090F"
GRIS="#848FA6"

mod() { # r c fill gap
  r=$1; c=$2; f=$3; g=$4
  x=$(awk "BEGIN{printf \"%g\", 20+$c*20+$g}")
  y=$(awk "BEGIN{printf \"%g\", 20+$r*20+$g}")
  s=$(awk "BEGIN{printf \"%g\", 20-2*$g}")
  printf '  <rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>\n' "$x" "$y" "$s" "$s" "$f"
}

frame() { # fill gap
  for c in 0 1 2 3 4; do mod 0 "$c" "$1" "$2"; done
  for r in 1 2 3; do mod "$r" 0 "$1" "$2"; done
  for c in 0 1 2 3 4; do mod 4 "$c" "$1" "$2"; done
}

head_svg() { # title
  printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 140" width="140" height="140" role="img" aria-label="%s"><title>%s</title>\n' "$1" "$1"
}

# 01 · Marca abierta sobre tinta (maestra)
{ head_svg "Cuadra · marca abierta"; frame "$FG" 2.5; echo '</svg>'; } > "$OUT/cuadra-simbolo-abierto.svg"

# 02 · Marca abierta en tinta (sobre claro)
{ head_svg "Cuadra · marca abierta sobre claro"; frame "$TINTA" 2.5; echo '</svg>'; } > "$OUT/cuadra-simbolo-abierto-tinta.svg"

# 03 · Marca cerrada (sello de conformidad)
{ head_svg "Cuadra · marca cerrada"; frame "$FG" 2.5
  for r in 1 2 3; do mod "$r" 4 "$SELLO" 2.5; done
  mod 2 2 "$SELLO" 2.5; echo '</svg>'; } > "$OUT/cuadra-simbolo-cerrado.svg"

# 04 · Marca observada (2 de 3 aceptadas)
{ head_svg "Cuadra · marca observada"; frame "$FG" 2.5
  mod 1 4 "$SELLO" 2.5; mod 2 4 "$SELLO" 2.5; mod 3 4 "$AMBAR" 2.5
  echo '</svg>'; } > "$OUT/cuadra-simbolo-observado.svg"

# 05 · Reducción: módulos macizos, sin separación (<48px)
{ head_svg "Cuadra · reducción"; frame "$FG" 0; echo '</svg>'; } > "$OUT/cuadra-simbolo-reduccion.svg"

# 06 · Monocromo gris (soportes sin acento)
{ head_svg "Cuadra · monocromo"; frame "$GRIS" 2.5
  for r in 1 2 3; do mod "$r" 4 "$GRIS" 2.5; done; echo '</svg>'; } > "$OUT/cuadra-simbolo-mono.svg"

# 07 · Favicon 32 (macizo, puerta cerrada para legibilidad en pestaña)
{ printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 140" width="32" height="32" role="img" aria-label="Cuadra"><title>Cuadra</title>\n'
  printf '  <rect width="140" height="140" fill="%s"/>\n' "$TINTA"
  frame "$FG" 0
  for r in 1 2 3; do mod "$r" 4 "$SELLO" 0; done
  echo '</svg>'; } > "$OUT/cuadra-favicon.svg"
