# Marco luminoso del metro de Montreal

[Français](../README.md) · [English](README_EN.md) · **Español** · [Italiano](README_IT.md)

![Concepto del marco luminoso del metro en un apartamento de Montreal](images/inspiration-salon.jpg)

Un marco mural de 18 × 24 pulgadas que anima los recorridos estimados del metro
de Montreal y muestra las perturbaciones de la red mediante 68 LED direccionables
y un Raspberry Pi Pico 2 W.

> Las posiciones son estimaciones calculadas a partir de los horarios GTFS. La
> STM no publica la posición real de los trenes del metro. Las alertas de
> servicio proceden de la API de estado de la STM.

## Un solo programa, cuatro idiomas

El asistente inicial detecta automáticamente el idioma del navegador y permite
elegir francés, inglés, español o italiano. El usuario puede cambiarlo en
cualquier momento y el navegador recuerda la selección. Los nombres oficiales
de las estaciones no se traducen.

No existen versiones distintas del firmware: todas las traducciones están en
una sola página ligera que únicamente se carga durante la asociación inicial.

## Inicio rápido

1. Instala [MicroPython para Pico 2 W](https://micropython.org/download/RPI_PICO2_W/).
2. Abre Thonny y selecciona **MicroPython (Raspberry Pi Pico)**.
3. Copia `pico/secrets.example.py` como `pico/secrets.py`.
4. Añade los datos de tu Wi-Fi de 2,4 GHz y la clave de la API STM.
5. Copia todos los archivos de [`pico/`](../pico) en la raíz `/` del Pico.
6. Reinicia el Pico.
7. Conéctate a `Metro-Setup` con la contraseña `metro-led-68`.
8. Abre `http://192.168.4.1`, elige el idioma y asocia cada LED que parpadea
   con la estación situada delante.

La cadena física de LED no tiene que seguir el orden geográfico de las estaciones.

## Probar sin equipo

```bash
python3 simulator/server.py
```

Abre `http://127.0.0.1:8765/` para el simulador o
`http://127.0.0.1:8765/setup-preview?lang=es` para el asistente inicial.

## Significado de las animaciones

| Animación | Significado |
|---|---|
| Color de línea en movimiento | Paso estimado de un tren |
| Dos estaciones vecinas parcialmente iluminadas | Tren estimado entre estaciones |
| Blanco | Estación de correspondencia |
| Pulsación ámbar | Servicio lento o perturbado |
| Parpadeo rojo | Línea interrumpida o estación cerrada |
| Respiración lenta y tenue | Modo nocturno |
| Magenta fijo al arrancar | Falta la configuración Wi-Fi |

## Seguridad eléctrica

El proyecto utiliza 68 píxeles WS2811 de 12 mm y 5 V. El Pico y los LED pueden
compartir una batería USB, pero los LED necesitan una rama de 5 V separada y
correctamente dimensionada.

- Nunca alimentes la cadena desde el pin `3V3` del Pico.
- Une obligatoriamente la masa del Pico y la de los LED.
- Desconecta la alimentación antes de modificar el cableado.
- Respeta el sentido `DATA IN → DATA OUT`.
- Mantén activados los límites de luminosidad y corriente del software.

Consulta la [guía técnica completa en francés](GUIDE_FR.md) para el cableado,
los diagnósticos, las actualizaciones GTFS y la construcción.
