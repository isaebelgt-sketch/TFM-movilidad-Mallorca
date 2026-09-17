# Índice de prioridad de intervención multimodal

## Propósito

Ordenar los 20 pares alojamiento-destino de la muestra para identificar casos que requieren revisión de accesibilidad o de servicio. No estima demanda, emisiones, causalidad ni calidad global de cada municipio.

## Componentes y pesos del escenario equilibrado

- Brecha de acceso a parada desde el alojamiento: 0,30.
- Brecha de acceso a parada desde el destino: 0,30.
- Restricción observada en el resultado OTP: 0,25.
- Carga de caminata de la alternativa multimodal, si existe: 0,15.

Las brechas de origen y destino se normalizan entre 400 y 1.200 m, límites utilizados ya en la línea base. La caminata multimodal se normaliza entre 1.600 y 2.400 m, equivalentes a dos accesos de 800 y 1.200 m.

## Robustez

Se recalcula el rango con cuatro conjuntos de pesos: equilibrado, foco en origen, foco en destino y foco en resultado de ruta. Un caso se considera robustamente prioritario si permanece entre los cinco primeros en al menos tres escenarios.

## Limitaciones

Los pesos y la codificación de resultados son decisiones explícitas del estudio y deben discutirse; por eso se entrega el análisis de sensibilidad. El índice se limita a la muestra y a las condiciones temporales del experimento OTP.
