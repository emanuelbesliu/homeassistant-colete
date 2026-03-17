# Colete - Integrare Home Assistant pentru Urmarirea Coletelor din Romania

[![GitHub Release](https://img.shields.io/github/v/release/emanuelbesliu/homeassistant-colete)](https://github.com/emanuelbesliu/homeassistant-colete/releases/latest)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/emanuelbesliu/homeassistant-colete)](LICENSE)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/emanuelbesliu)

Integrare Home Assistant pentru urmarirea coletelor din Romania. Suporta curieri multipli cu detectare automata si urmarire in timp real prin numarul AWB.

## Curieri Suportati

| Curier | API | Autentificare |
|--------|-----|---------------|
| **Sameday** | API publica JSON | Nu necesita |
| **FAN Courier** | API publica JSON | Nu necesita |

Se pot adauga curieri noi in versiuni viitoare (Cargus, DPD, Posta Romana etc.).

## Functionalitati

### Urmarire Colete
- **Status** - Statusul curent al coletului (normalizat: In Transit, Out for Delivery, Delivered etc.)
- **Locatie** - Ultima locatie cunoscuta a coletului
- **Ultima Actualizare** - Data/ora ultimei actualizari de la curier
- **Livrare** - Starea livrarii (Pending, Ready for Pickup, Delivered)

### Detectare Lockere/Easybox
- Detecteaza automat cand coletul a fost depozitat intr-un **Easybox** (Sameday) sau **FANbox** (FAN Courier)
- Status distinct: **Ready for Pickup** - coletul este la locker, nu a fost livrat definitiv
- Continua monitorizarea pana la ridicarea coletului

### Detectare Automata Curier
- Selecteaza "Auto-detect" si integrarea incearca fiecare curier in ordine pana gaseste date pentru AWB-ul respectiv

### Arhivare Automata
- Coletele livrate/returnate/anulate sunt arhivate automat dupa **30 de zile**

### Serviciu pentru Automatizari
- Serviciul `colete.track_parcel` permite adaugarea programatica de colete (ex: din automatizari care parseaza email-uri de confirmare comanda)

## Instalare

### Metoda 1: HACS (Recomandat)

1. Deschide HACS in Home Assistant
2. Click pe "Integrations"
3. Click pe meniul cu 3 puncte -> "Custom repositories"
4. Adauga: `https://github.com/emanuelbesliu/homeassistant-colete`
5. Categorie: "Integration"
6. Cauta "Colete" si instaleaza
7. Reporneste Home Assistant

### Metoda 2: Manual

```bash
cd /config
mkdir -p custom_components
cd custom_components
git clone https://github.com/emanuelbesliu/homeassistant-colete.git colete_tmp
mv colete_tmp/custom_components/colete .
rm -rf colete_tmp
```

Reporneste Home Assistant.

## Configurare

### Pas 1: Adauga un Colet

1. In Home Assistant, mergi la **Settings -> Devices & Services**
2. Click pe **+ Add Integration**
3. Cauta "**Colete**"
4. Selecteaza curierul (sau Auto-detect)
5. Introdu numarul AWB
6. Optional: seteaza un nume prietenos si intervalul de actualizare
7. Click **Submit**

Fiecare colet urmarit este o intrare separata. Poti adauga cate colete doresti.

### Pas 2: Configureaza Optiuni (Optional)

1. Mergi la **Settings -> Devices & Services -> Colete -> Configure** (pe intrarea dorita)
2. Modifica numele prietenos sau intervalul de actualizare

### Pas 3: Verifica Senzorii Creati

Dupa configurare, pentru fiecare colet vei avea 4 senzori:

| Senzor | Descriere | Exemplu Valoare |
|--------|-----------|-----------------|
| Status | Statusul curent al coletului | In Transit |
| Location | Ultima locatie cunoscuta | Bucuresti - Hub Sortare |
| Last Update | Data ultimei actualizari | 2026-03-15 14:30 |
| Delivery | Starea livrarii | Pending / Ready for Pickup / Delivered |

### Statusuri Normalizate

| Status | Descriere |
|--------|-----------|
| Unknown | Status necunoscut |
| Picked Up | Coletul a fost preluat de curier |
| In Transit | In tranzit |
| Out for Delivery | In curs de livrare |
| Ready for Pickup | Disponibil la locker (Easybox/FANbox) |
| Delivered | Livrat |
| Returned | Returnat expeditorului |
| Canceled | Anulat |

## Utilizare

### Atribute Disponibile

Senzorul **Status** expune atribute suplimentare:

```yaml
# Exemplu: sensor.colete_sameday_123456789_status
attributes:
  awb: "123456789"
  courier: "Sameday"
  status_detail: "Coletul a fost livrat"
  status_normalized: "delivered"
  events:
    - status: "Predat de expeditor"
      date: "2026-03-14 10:00"
      location: "Cluj-Napoca"
    - status: "In tranzit"
      date: "2026-03-14 18:00"
      location: "Bucuresti - Hub Sortare"
  event_count: 2
  weight: 1.5
```

Senzorul **Delivery** include detalii de confirmare:

```yaml
# sensor.colete_sameday_123456789_delivery
attributes:
  awb: "123456789"
  courier: "Sameday"
  delivered: true
  delivered_to: "Ion Popescu"
  delivered_date: "2026-03-15 14:30"
```

### Serviciu: colete.track_parcel

Adauga un colet nou programatic, util pentru automatizari:

```yaml
action: colete.track_parcel
data:
  awb: "987654321"
  courier: "auto"  # sau "sameday", "fan_courier"
  friendly_name: "Laptop nou"
```

### Exemple Automatizari

#### Notificare Colet Livrat

```yaml
alias: "Notificare Colet Livrat"
description: "Trimite notificare cand un colet este livrat"
mode: single

triggers:
  - entity_id: sensor.colete_sameday_123456789_delivery
    to: "Delivered"
    trigger: state

actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "Colet Livrat!"
      message: >-
        Coletul {{ state_attr('sensor.colete_sameday_123456789_status', 'awb') }}
        a fost livrat.
```

#### Notificare Colet la Easybox

```yaml
alias: "Notificare Colet la Easybox"
description: "Trimite notificare cand un colet este disponibil la locker"
mode: single

triggers:
  - entity_id: sensor.colete_sameday_123456789_delivery
    to: "Ready for Pickup"
    trigger: state

actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "Colet la Easybox!"
      message: >-
        Coletul {{ state_attr('sensor.colete_sameday_123456789_status', 'awb') }}
        este disponibil pentru ridicare.
```

#### Adauga Colet din Email (cu Automatizare)

```yaml
alias: "Track Parcel from Email"
description: "Adauga automat colete noi din email-urile de confirmare comanda"
mode: queued

triggers:
  - trigger: event
    event_type: email_new_delivery_notification

actions:
  - action: colete.track_parcel
    data:
      awb: "{{ trigger.event.data.awb }}"
      courier: "auto"
      friendly_name: "{{ trigger.event.data.subject }}"
```

### Exemple Dashboard

#### Card Colete Active

```yaml
type: entities
title: Colete in Curs
entities:
  - entity: sensor.colete_sameday_123456789_status
    name: Laptop
  - entity: sensor.colete_sameday_123456789_location
    name: Locatie Laptop
  - entity: sensor.colete_fan_courier_987654321_status
    name: Telefon
  - entity: sensor.colete_fan_courier_987654321_delivery
    name: Livrare Telefon
```

## Despre Date

### Sursa Datelor

- **Sameday**: `https://api.sameday.ro/api/public/awb/{AWB}/awb-history` - API publica JSON
- **FAN Courier**: `https://www.fancourier.ro/limit-tracking.php` - API publica JSON

### Frecventa Actualizare

- Implicit: **15 minute** (configurabil: 5 minute - 1 ora)
- Coletele in statusuri terminale (delivered, returned, canceled) continua sa fie monitorizate pentru 30 de zile
- Coletele la locker (ready_for_pickup) continua sa fie monitorizate activ

### Limitari

- Doar Sameday si FAN Courier suportate in v1.0.0
- FAN Courier poate returna eroare 429 (rate limit) daca sunt prea multe cereri
- Coletele foarte vechi pot fi sterse din sistemele curierilor si nu vor mai returna date

## Troubleshooting

### Senzorii arata "unavailable"

1. Verificati conexiunea la internet
2. Verificati logurile: **Settings -> System -> Logs**, cautati "colete"
3. Verificati ca numarul AWB este corect si exista in sistemul curierului
4. Posibil ca API-ul curierului sa fie temporar indisponibil

### AWB-ul nu este gasit

1. Verificati ca ati selectat curierul corect, sau folositi Auto-detect
2. Sameday si FAN Courier au formate diferite de AWB
3. AWB-ul poate sa nu fie inca inregistrat in sistem (asteptati cateva ore dupa expedierea coletului)

### Eroare la configurare

1. Verificati ca aveti acces la internet
2. Verificati ca numarul AWB este valid si recunoscut de cel putin un curier
3. Verificati logurile pentru detalii despre eroare

## Structura Fisierelor

```
custom_components/colete/
  __init__.py           # Entry point, service registration
  manifest.json         # Metadata integrare
  const.py              # Constante, statusuri, configuratie senzori
  api.py                # Client API multi-curier
  coordinator.py        # Data Update Coordinator
  config_flow.py        # Configurare UI + service flow
  sensor.py             # Entitati senzor (4 per colet)
  services.yaml         # Definitie serviciu track_parcel
  strings.json          # Stringuri traducere (EN)
  translations/
    en.json             # Traduceri engleza
    ro.json             # Traduceri romana
```

## Contributii

Contributiile sunt binevenite! Pentru bug-uri sau feature requests, deschideti un issue pe GitHub.

### Adaugarea unui Curier Nou

Pentru a adauga un curier nou:
1. Adaugati constantele in `const.py` (URL API, coduri status, keywords locker)
2. Implementati parser-ul in `api.py` (metoda `_parse_<courier>()`)
3. Adaugati curierul in `COURIERS` si `COURIER_DETECT_ORDER`
4. Adaugati traducerile in `strings.json`, `en.json`, `ro.json`

## Licenta

MIT License - Vezi [LICENSE](LICENSE) pentru detalii.

## Support

- **GitHub Issues**: [Raportati probleme](https://github.com/emanuelbesliu/homeassistant-colete/issues)
- **Home Assistant Community**: [Forum discutii](https://community.home-assistant.io/)

---

## Support the Developer

If you find this project useful, consider buying me a coffee!

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/emanuelbesliu)

---

*Aceasta integrare nu este afiliata oficial cu Sameday sau FAN Courier.*
*Datele sunt furnizate prin API-uri publice ale curierilor.*
