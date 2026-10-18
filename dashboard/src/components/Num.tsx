import { useEffect, useRef, useState } from "react";

const reduce = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Número que cuenta hasta su valor cuando cambia (700 ms, ease-out). `null` se muestra como "–". */
export function Num({ value, format }: { value: number | null | undefined; format: (v: number) => string }) {
  const [shown, setShown] = useState(0);
  const from = useRef(0);

  useEffect(() => {
    if (value == null) return;
    if (reduce()) {
      setShown(value);
      from.current = value;
      return;
    }
    const start = performance.now();
    const a = from.current;
    let id = 0;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 700);
      const v = a + (value - a) * (1 - Math.pow(1 - t, 3));
      from.current = t === 1 ? value : v;
      setShown(from.current);
      if (t < 1) id = requestAnimationFrame(step);
    };
    id = requestAnimationFrame(step);
    // si el valor cambia a mitad de camino, la próxima animación sigue desde donde quedó
    return () => cancelAnimationFrame(id);
  }, [value]);

  return <>{value == null ? "–" : format(shown)}</>;
}
