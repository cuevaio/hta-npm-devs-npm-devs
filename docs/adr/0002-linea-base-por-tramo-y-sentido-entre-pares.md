# La línea base es por tramo y sentido entre pares, no por vehículo

El perfil de la flota muestra que la pendiente domina el consumo: subiendo el paso de Nanling la mediana es 79,7 L/100 km y bajando 10,8 ([`fead-perfil-piloto.md`](../research/fead-perfil-piloto.md)). Una línea base por vehículo marcaría sobreconsumo en cada subida. Por eso el consumo esperado de un tramo se calcula con los pares que recorrieron ese mismo tramo del corredor en el mismo sentido, y el sobreconsumo se mide contra esa referencia.

## Considered Options

- **Por vehículo (su propio histórico):** descartada por los falsos positivos en subidas.
- **Modelo supervisado rpm/acelerador/par (R² 0,87 en el paper):** explica el consumo instantáneo, pero no dice si un vehículo gasta más que sus pares en las mismas condiciones; puede servir como evidencia secundaria.

## Consequences

- El dataset no trae altitud: el efecto de la pendiente se captura implícitamente al comparar el mismo tramo, sin modelarla.
- Hacen falta suficientes pares por tramo; corredores con un solo vehículo no tienen línea base.
