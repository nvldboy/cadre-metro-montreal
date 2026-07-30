# Cornice luminosa della metropolitana di Montréal

[Français](../README.md) · [English](README_EN.md) · [Español](README_ES.md) · **Italiano**

![Progetto della cornice luminosa in un appartamento di Montréal](images/inspiration-salon.jpg)

Una cornice da parete di 18 × 24 pollici che anima i passaggi stimati della
metropolitana di Montréal e segnala le perturbazioni della rete tramite 68 LED
indirizzabili e un Raspberry Pi Pico 2 W.

> Le posizioni sono stime calcolate dagli orari GTFS. La STM non pubblica la
> posizione reale dei treni della metropolitana. Gli avvisi di servizio
> provengono dall’API sullo stato della rete STM.

## Un solo programma, quattro lingue

L’assistente iniziale rileva automaticamente la lingua del browser e consente
di scegliere francese, inglese, spagnolo o italiano. La scelta può essere
modificata in qualsiasi momento e viene ricordata dal browser. I nomi ufficiali
delle stazioni restano invariati.

Non esistono versioni separate del firmware: tutte le traduzioni sono contenute
in un’unica pagina leggera, caricata solo durante l’associazione iniziale.

## Avvio rapido

1. Installa [MicroPython per Pico 2 W](https://micropython.org/download/RPI_PICO2_W/).
2. Apri Thonny e seleziona **MicroPython (Raspberry Pi Pico)**.
3. Copia `pico/secrets.example.py` come `pico/secrets.py`.
4. Inserisci i dati della rete Wi-Fi a 2,4 GHz e la chiave API STM.
5. Copia tutti i file di [`pico/`](../pico) nella directory principale `/` del Pico.
6. Riavvia il Pico.
7. Collegati a `Metro-Setup` con la password `metro-led-68`.
8. Apri `http://192.168.4.1`, scegli la lingua e associa ogni LED lampeggiante
   alla stazione che si trova davanti.

La catena fisica dei LED non deve seguire l’ordine geografico delle stazioni.

## Prova senza hardware

```bash
python3 simulator/server.py
```

Apri `http://127.0.0.1:8765/` per il simulatore oppure
`http://127.0.0.1:8765/setup-preview?lang=it` per l’assistente iniziale.

## Significato delle animazioni

| Animazione | Significato |
|---|---|
| Colore della linea in movimento | Passaggio stimato di un treno |
| Due stazioni vicine parzialmente illuminate | Treno stimato fra le stazioni |
| Bianco | Stazione di interscambio |
| Pulsazione ambra | Servizio rallentato o perturbato |
| Lampeggio rosso | Linea interrotta o stazione chiusa |
| Respirazione lenta e tenue | Modalità notturna |
| Magenta fisso all’avvio | Configurazione Wi-Fi mancante |

## Sicurezza elettrica

Il progetto usa 68 pixel WS2811 da 12 mm e 5 V. Il Pico e i LED possono
condividere una batteria USB, ma i LED richiedono un ramo separato a 5 V
correttamente dimensionato.

- Non alimentare mai la catena tramite il pin `3V3` del Pico.
- La massa del Pico e quella dei LED devono essere collegate.
- Scollega l’alimentazione prima di modificare i cavi.
- Rispetta la direzione `DATA IN → DATA OUT`.
- Mantieni attivi i limiti software di luminosità e corrente.

Consulta la [guida tecnica completa in francese](GUIDE_FR.md) per cablaggio,
diagnostica, aggiornamenti GTFS e costruzione.
