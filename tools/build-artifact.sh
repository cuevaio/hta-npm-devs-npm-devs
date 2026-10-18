#!/bin/sh
# Genera la versión publicable como Artifact de Claude a partir de web/index.html:
# quita el esqueleto del documento (el servicio lo pone) e incrusta tokens.css,
# porque el Artifact no resuelve la hoja de estilos relativa del repositorio.
# Uso:  sh tools/build-artifact.sh  ->  build/cuadra-landing.html
set -e
cd "$(dirname "$0")/.."
mkdir -p build
awk '
  /^<!doctype html>$/ {next}
  /^<html lang="es">$/ {next}
  /^<head>$/ {next}
  /^<\/head>$/ {next}
  /^<body>$/ {next}
  /^<\/body>$/ {next}
  /^<\/html>$/ {next}
  /^<meta charset=/ {next}
  /^<meta name="viewport"/ {next}
  /^<link rel="icon"/ {next}
  /^<link rel="stylesheet" href="assets\/tokens.css">$/ {
    print "<style>";
    while ((getline line < "web/assets/tokens.css") > 0) print line;
    close("web/assets/tokens.css");
    print "</style>";
    next
  }
  {print}
' web/index.html > build/cuadra-landing.html
echo "build/cuadra-landing.html listo"
