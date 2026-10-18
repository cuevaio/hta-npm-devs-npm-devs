import { useEffect, useRef, useState } from "react";

export type Polled<T> = { status: "loading" | "ok" | "error"; data?: T };

/**
 * Llama a `fn` ahora y, cuando termina, otra vez a los `ms`. Nunca hay dos llamadas en vuelo: con
 * setInterval, un backend lento acumulaba peticiones hasta saturarse (Cloud Run respondió 429).
 * Ante un error conserva el último dato y reintenta en el próximo ciclo.
 */
export function usePolling<T>(fn: () => Promise<T>, ms = 2000): Polled<T> {
  const [state, setState] = useState<Polled<T>>({ status: "loading" });
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    let alive = true;
    let id: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      try {
        const data = await ref.current();
        if (alive) setState({ status: "ok", data });
      } catch {
        if (alive) setState((s) => ({ status: "error", data: s.data }));
      }
      if (alive) id = setTimeout(tick, ms);
    };
    void tick();
    return () => {
      alive = false;
      clearTimeout(id);
    };
  }, [ms]);
  return state;
}
