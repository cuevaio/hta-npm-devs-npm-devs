# El dashboard usa React

El dashboard tiene tres paneles que se refrescan cada 2 s (vehículos y viajes, mapa del replay, alertas) más un panel de detalle por viaje. Elegimos React + Vite sobre TypeScript sin framework porque los implementadores (agentes) lo escriben con menos errores, hay integración madura con MapLibre y Recharts, y el estado compartido entre paneles se expresa mejor en componentes.
