"""Limiti ai tentativi: login sbagliati e registrazioni a raffica."""

import time
from collections import deque

WINDOW_SECONDS = 15 * 60


class AttemptLimiter:
    """Conta i tentativi per chiave (IP, IP + email...) nell'ultima finestra di tempo.

    Tiene tutto in memoria: basta per un solo processo. Con più server dietro
    un bilanciatore servirebbe un archivio condiviso, per esempio Redis.
    """

    def __init__(self, max_attempts: int, window: int = WINDOW_SECONDS):
        self.max_attempts = max_attempts
        self.window = window
        self._attempts: dict[str, deque[float]] = {}

    def _recent(self, key: str) -> int:
        attempts = self._attempts.get(key)
        if attempts is None:
            return 0
        limit = time.monotonic() - self.window
        while attempts and attempts[0] < limit:
            attempts.popleft()
        if not attempts:
            # Chiavi scelte da un attaccante non devono restare in memoria per sempre
            del self._attempts[key]
            return 0
        return len(attempts)

    def is_blocked(self, key: str) -> bool:
        return self._recent(key) >= self.max_attempts

    def record(self, key: str) -> None:
        self._recent(key)
        self._attempts.setdefault(key, deque()).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def reset_all(self) -> None:
        self._attempts.clear()


# 5 password sbagliate per la stessa email dallo stesso IP. La chiave è la coppia:
# così uno sconosciuto non può bloccare il tuo account sbagliando apposta da casa sua.
login_limiter = AttemptLimiter(max_attempts=5)
# Un IP che prova tante email diverse viene fermato lo stesso, un po' più in là
ip_limiter = AttemptLimiter(max_attempts=20)
# Registrazioni: ognuna costa un hash Argon2, non lasciamo che un bot ne faccia mille
signup_limiter = AttemptLimiter(max_attempts=10, window=60 * 60)
# Attività demo nuove per IP in un'ora: ognuna occupa spazio nel database per 24 ore
demo_limiter = AttemptLimiter(max_attempts=10, window=60 * 60)
