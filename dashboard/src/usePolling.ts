import { useEffect, useRef, useState } from "react";

export type Polled<T> = { status: "loading" | "ok" | "error"; data?: T };

/** Llama a `fn` ahora y cada `ms`. Ante un error conserva el último dato y reintenta en el próximo ciclo. */
export function usePolling<T>(fn: () => Promise<T>, ms = 2000): Polled<T> {
  const [state, setState] = useState<Polled<T>>({ status: "loading" });
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await ref.current();
        if (alive) setState({ status: "ok", data });
      } catch {
        if (alive) setState((s) => ({ status: "error", data: s.data }));
      }
    };
    void tick();
    const id = setInterval(tick, ms);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [ms]);
  return state;
}
