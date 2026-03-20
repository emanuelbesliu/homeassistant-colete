# Colete - Integrare Home Assistant pentru Urmarirea Coletelor din Romania

[![GitHub Release](https://img.shields.io/github/v/release/emanuelbesliu/homeassistant-colete)](https://github.com/emanuelbesliu/homeassistant-colete/releases/latest)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/emanuelbesliu/homeassistant-colete)](LICENSE)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/emanuelbesliu)

Integrare Home Assistant pentru urmarirea coletelor din Romania. Suporta curieri multipli cu detectare automata si urmarire in timp real prin numarul AWB.

## Curieri Suportati

| Curier | API | Autentificare | Date Disponibile |
|--------|-----|---------------|------------------|
| **Sameday** | API publica JSON | Nu necesita | Status, locatie, istoric evenimente, greutate |
| **FAN Courier** | API publica JSON | Nu necesita | Status, locatie, istoric evenimente |
| **Cargus** | HTML scraping | Nu necesita | Status, progres %, fara istoric/locatie |
| **GLS Romania** | API publica JSON | Nu necesita | Status, progres %, fara istoric/locatie |
| **DPD Romania** | API publica JSON | Nu necesita | Status, locatie, istoric evenimente, destinatar |

## Functionalitati

### Urmarire Colete
- **Status** - Statusul curent al coletului (normalizat: In Transit, Out for Delivery, Delivered etc.)
- **Locatie** - Ultima locatie cunoscuta a coletului
- **Ultima Actualizare** - Data/ora ultimei actualizari de la curier
- **Livrare** - Starea livrarii (Pending, Ready for Pickup, Delivered)

### Scanner Email IMAP (NOU)
- **Scanare automata email** — se conecteaza la casuta de email via IMAP SSL si cauta numere AWB in email-urile primite
- **Extractie inteligenta** — detecteaza numere AWB pe baza cuvintelor cheie (AWB, tracking, numar de urmarire, colet, expediere, livrare) cu regex generice, nu pe baza expeditorului
- **Detectare curier din domeniu** — daca email-ul vine de la `@sameday.ro`, `@fancourier.ro`, `@cargus.ro`, `@gls-romania.ro` sau `@dpd.ro`, sugereaza curierul corect (altfel foloseste auto-detect)
- **Deduplicare persistenta** — AWB-urile deja procesate sunt memorate (chiar si dupa restart HA) si nu sunt procesate din nou
- **Creare automata colete** — pentru fiecare AWB nou gasit, apeleaza automat serviciul `colete.track_parcel` pentru a crea o intrare de urmarire
- **3 senzori dedicati**: Scanner Status (connected/scanning/error), Last Scan (timestamp), AWBs Found (total)
- Suporta **Gmail** (cu App Password), **Outlook**, **Yahoo**, sau orice server IMAP SSL

### Detectare Lockere/Easybox/Parcel Shop
- Detecteaza automat cand coletul a fost depozitat intr-un **Easybox** (Sameday), **FANbox** (FAN Courier), **GLS Parcel Shop** sau **DPD Pickup Shop**
- Status distinct: **Ready for Pickup** - coletul este la locker/parcel shop, nu a fost livrat definitiv
- Continua monitorizarea pana la ridicarea coletului

### Detectare Automata Curier
- Selecteaza "Auto-detect" si integrarea incearca fiecare curier in ordine pana gaseste date pentru AWB-ul respectiv

### Arhivare Automata
- Coletele livrate/returnate/anulate sunt arhivate automat dupa un numar configurabil de zile (implicit **30 de zile**, 0 = pastrare permanenta)
- Numarul de zile se configureaza per colet la adaugare sau din Options flow
- Numaratoarea incepe de la data reala de livrare (din datele curierului)

### Progres Livrare
- **Cargus** si **GLS** expun procentul de progres al livrarii (`progress_pct`) ca atribut al senzorului Status
- Util pentru bare de progres in dashboard

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

La adaugarea integrarii, vei vedea un **meniu** cu doua optiuni:
- **Track a Parcel** — adauga manual un colet cu numar AWB
- **Set up Email Scanner** — configureaza scanarea automata a email-urilor pentru AWB-uri

### Optiunea 1: Adauga un Colet

1. In Home Assistant, mergi la **Settings -> Devices & Services**
2. Click pe **+ Add Integration**
3. Cauta "**Colete**"
4. Selecteaza **Track a Parcel**
5. Selecteaza curierul (sau Auto-detect)
6. Introdu numarul AWB
7. Optional: seteaza un nume prietenos si intervalul de actualizare
8. Click **Submit**

Fiecare colet urmarit este o intrare separata. Poti adauga cate colete doresti.

### Optiunea 2: Configureaza Scanner Email (IMAP)

1. In Home Assistant, mergi la **Settings -> Devices & Services**
2. Click pe **+ Add Integration**
3. Cauta "**Colete**"
4. Selecteaza **Set up Email Scanner**
5. Completeaza datele serverului IMAP:

| Camp | Descriere | Exemplu |
|------|-----------|---------|
| IMAP Server | Adresa serverului IMAP | `imap.gmail.com` |
| IMAP Port | Port SSL (implicit 993) | `993` |
| Email | Adresa de email | `user@gmail.com` |
| Password | Parola sau App Password | (vezi nota mai jos) |
| Folder | Folderul de scanat (implicit INBOX) | `INBOX` |
| Lookback Days | Cate zile in urma sa caute (implicit 7) | `7` |
| Scan Interval | Frecventa scanarii in secunde (implicit 300 = 5 min) | `300` |

6. Click **Submit** — integrarea va verifica conexiunea IMAP inainte de salvare

> **Gmail**: Trebuie sa folosesti un **App Password**, nu parola contului. Genereaza unul din:
> [Google Account > Security > App Passwords](https://myaccount.google.com/apppasswords)
> (necesita 2FA activat pe cont)

> **Outlook/Hotmail**: Activeaza IMAP din setarile contului si foloseste App Password daca ai 2FA.

### Configureaza Optiuni (Optional)

1. Mergi la **Settings -> Devices & Services -> Colete -> Configure** (pe intrarea dorita)
2. **Pentru colete**: Modifica numele prietenos, intervalul de actualizare sau zilele de retentie
3. **Pentru scanner IMAP**: Modifica folderul, zilele lookback sau intervalul de scanare

### Verifica Senzorii Creati

Dupa configurare, **pentru fiecare colet** vei avea 4 senzori:

| Senzor | Descriere | Exemplu Valoare |
|--------|-----------|-----------------|
| Status | Statusul curent al coletului | In Transit |
| Location | Ultima locatie cunoscuta | Bucuresti - Hub Sortare |
| Last Update | Data ultimei actualizari | 2026-03-15 14:30 |
| Delivery | Starea livrarii | Pending / Ready for Pickup / Delivered |

**Pentru scanner-ul IMAP** vei avea 3 senzori:

| Senzor | Descriere | Exemplu Valoare |
|--------|-----------|-----------------|
| Scanner Status | Starea scanner-ului | connected / scanning / error |
| Last Scan | Timestamp-ul ultimei scanari | 2026-03-20 10:15 |
| AWBs Found | Numarul total de AWB-uri gasite | 5 |

### Statusuri Normalizate

| Status | Descriere |
|--------|-----------|
| Unknown | Status necunoscut |
| Picked Up | Coletul a fost preluat de curier |
| In Transit | In tranzit |
| Out for Delivery | In curs de livrare |
| Ready for Pickup | Disponibil la locker (Easybox/FANbox/GLS Parcel Shop/DPD Pickup Shop) |
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
  courier: "auto"  # sau "sameday", "fan_courier", "cargus", "gls", "dpd"
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

#### Adauga Colet din Email (Automat cu IMAP Scanner)

Scanner-ul IMAP se ocupa automat de aceasta functionalitate. Configureaza scanner-ul email (vezi sectiunea Configurare) si coletele vor fi adaugate automat cand primesti email-uri de expediere cu numere AWB.

Daca preferi o abordare manuala cu event-uri custom:

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
    name: Laptop (Sameday)
  - entity: sensor.colete_sameday_123456789_location
    name: Locatie Laptop
  - entity: sensor.colete_fan_courier_987654321_status
    name: Telefon (FAN)
  - entity: sensor.colete_fan_courier_987654321_delivery
    name: Livrare Telefon
  - entity: sensor.colete_cargus_111222333_status
    name: Haine (Cargus)
  - entity: sensor.colete_gls_6234776771_status
    name: Casti (GLS)
  - entity: sensor.colete_dpd_09981100001234_status
    name: Pantofi (DPD)
```

## Despre Date

### Sursa Datelor

- **Sameday**: `https://api.sameday.ro/api/public/awb/{AWB}/awb-history` - API publica JSON
- **FAN Courier**: `https://www.fancourier.ro/limit-tracking.php` - API publica JSON
- **Cargus**: `https://www.cargus.ro/personal/urmareste-coletul/?tracking_number={AWB}` - HTML scraping (nu exista API publica JSON)
- **GLS Romania**: `https://gls-group.eu/app/service/open/rest/RO/ro/rstt029` - API publica JSON
- **DPD Romania**: `https://tracking.dpd.de/rest/plc/ro_RO/{AWB}` - API publica JSON (via DPD Germany tracking)

### Frecventa Actualizare

- Implicit: **15 minute** (configurabil: 5 minute - 1 ora)
- Coletele in statusuri terminale (delivered, returned, canceled) continua sa fie monitorizate conform `retention_days` configurat (implicit 30 zile)
- Coletele la locker (ready_for_pickup) continua sa fie monitorizate activ

### Limitari

- **Cargus**: Nu are API publica JSON; datele sunt extrase prin HTML scraping, ceea ce poate fi fragil la schimbari de design. Nu expune istoric evenimente sau locatie.
- **GLS Romania**: API-ul nu returneaza istoric evenimente, locatie sau greutate. Doar status curent si progres.
- **FAN Courier** poate returna eroare 429 (rate limit) daca sunt prea multe cereri
- **DPD Romania** poate returna eroare 429 (rate limit); API-ul este gazduit de DPD Germania si nu necesita autentificare
- Coletele foarte vechi pot fi sterse din sistemele curierilor si nu vor mai returna date
- Curieri nesuportati: Posta Romana (CAPTCHA Cloudflare)

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
  __init__.py           # Entry point, service registration, IMAP/parcel routing
  manifest.json         # Metadata integrare
  const.py              # Constante, statusuri, configuratie senzori, IMAP patterns
  api.py                # Client API multi-curier
  coordinator.py        # Data Update Coordinator (colete)
  imap_scanner.py       # Scanner IMAP — conectare, cautare, extractie AWB
  imap_coordinator.py   # IMAP Data Update Coordinator cu deduplicare persistenta
  config_flow.py        # Configurare UI (meniu, colet, IMAP) + service flow
  sensor.py             # Entitati senzor (4 per colet + 3 per scanner IMAP)
  services.yaml         # Definitie serviciu track_parcel
  strings.json          # Stringuri traducere (EN)
  translations/
    en.json             # Traduceri engleza
    ro.json             # Traduceri romana
  brand/
    icon.png            # Iconita integrare (256x256)
    icon@2x.png         # Iconita integrare HiDPI (512x512)
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

*Aceasta integrare nu este afiliata oficial cu Sameday, FAN Courier, Cargus, GLS sau DPD.*
*Datele sunt furnizate prin API-uri publice ale curierilor.*
*Functionalitatea IMAP necesita acces la o casuta de email — credentialele sunt stocate local in Home Assistant.*
