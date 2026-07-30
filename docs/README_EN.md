# Montréal Metro Light Frame

[Français](../README.md) · **English** · [Español](README_ES.md) · [Italiano](README_IT.md)

![Concept of the metro light frame in a Montréal apartment](images/inspiration-salon.jpg)

An 18 × 24 in wall frame that animates estimated Montréal metro trips and
displays network disruptions using 68 addressable LEDs and a Raspberry Pi
Pico 2 W.

> Train positions are estimates calculated from scheduled GTFS data. The STM
> does not publish real-time metro train positions. Service alerts are obtained
> from the STM service-status API.

## One program, four languages

The first-run assistant automatically detects the browser language and supports
French, English, Spanish and Italian. The user can switch languages at any time,
and the preference is remembered by the browser. Official station names remain
unchanged.

There are no separate firmware versions: all translations are contained in one
small setup page that is loaded only during the initial LED mapping.

## Quick start

1. Install [MicroPython for Pico 2 W](https://micropython.org/download/RPI_PICO2_W/).
2. Open Thonny and select **MicroPython (Raspberry Pi Pico)**.
3. Copy `pico/secrets.example.py` to `pico/secrets.py`.
4. Add your 2.4 GHz Wi-Fi credentials and STM API key.
5. Copy every file from [`pico/`](../pico) to the Pico root directory `/`.
6. Restart the Pico.
7. Join `Metro-Setup` with password `metro-led-68`.
8. Open `http://192.168.4.1`, choose your language and match each blinking LED
   to the station in front of it.

The physical LED chain does not need to follow the geographic station order.

## Try it without hardware

```bash
python3 simulator/server.py
```

Open `http://127.0.0.1:8765/` for the simulator or
`http://127.0.0.1:8765/setup-preview?lang=en` for the setup assistant.

## Animation meanings

| Animation | Meaning |
|---|---|
| Moving line colour | Estimated train passage |
| Two partially lit adjacent stations | Train estimated between stations |
| White | Transfer station |
| Amber pulse | Delayed or disrupted service |
| Red blink | Interrupted line or closed station |
| Slow dim breathing | Night mode |
| Solid magenta at startup | Missing Wi-Fi configuration |

## Electrical safety

The project targets 68 12 mm, 5 V WS2811 pixels. The Pico and LEDs may share
one USB battery, but the LEDs need a properly sized separate 5 V branch.

- Never power the LED chain through the Pico `3V3` pin.
- The Pico and LED grounds must be connected.
- Disconnect power before changing wiring.
- Follow the `DATA IN → DATA OUT` direction.
- Keep the built-in software brightness and current limits enabled.

See the [complete French technical guide](GUIDE_FR.md) for wiring, diagnostics,
GTFS updates and construction details.
