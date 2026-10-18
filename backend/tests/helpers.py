"""Constantes y reloj falso compartidos por los tests."""

from datetime import UTC, datetime, timedelta

KEY = {"X-API-Key": "secreta"}
# Fin de la historia en el fixture chico: T07 queda partido en historia y por reproducir.
REPLAY_START = datetime(2020, 4, 1, 20, 20, tzinfo=UTC)
T0 = datetime(2030, 1, 1, tzinfo=UTC)  # inicio del reloj falso


class FakeClock:
    def __init__(self):
        self.now = T0

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> datetime:
        self.now += timedelta(**kwargs)
        return self.now
