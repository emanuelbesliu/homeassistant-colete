# Colete - Urmărire Colete România (Home Assistant)

Integrare pentru urmărirea coletelor din România, cu suport pentru mai mulți curieri.

## Funcționalități

- Urmărire colete Sameday (inclusiv easybox)
- Urmărire colete FAN Courier (inclusiv FANbox)
- Auto-detectare curier după numărul AWB
- Detectare automată status locker/easybox/FANbox ("Gata de ridicare")
- 4 senzori per colet: Status, Locație, Ultima Actualizare, Livrare
- Arhivare automată a coletelor livrate după 30 zile
- Serviciu `colete.track_parcel` pentru adăugare din automatizări
- Nu necesită autentificare - API-uri publice
- Actualizare automată la fiecare 15 minute (configurabil)
- Traduceri complete română/engleză

## Instalare

### HACS (Recomandat)

1. Deschide HACS în Home Assistant
2. Click pe "Integrations"
3. Click pe meniul cu 3 puncte -> "Custom repositories"
4. Adaugă: `https://github.com/emanuelbesliu/homeassistant-colete`
5. Categorie: "Integration"
6. Caută "Colete" și instalează

### Manual

```bash
cd /config/custom_components
git clone https://github.com/emanuelbesliu/homeassistant-colete.git colete
mv colete/custom_components/colete/* colete/
rm -rf colete/custom_components
```

## Configurare

1. Reporniți Home Assistant
2. **Settings -> Devices & Services -> Add Integration**
3. Căutați "Colete"
4. Introduceți numărul AWB și selectați curierul (sau Auto-detect)
5. Opțional: adăugați un nume personalizat și ajustați intervalul de actualizare

## Curieri Suportați

| Curier | Locker | Status |
|--------|--------|--------|
| Sameday | easybox | Suportat |
| FAN Courier | FANbox | Suportat |

## Documentație Completă

Vezi [README complet](README.md) pentru:
- Lista completă a senzorilor și atributelor
- Exemple de automatizări
- Serviciul colete.track_parcel
- Troubleshooting

## Support

- [GitHub Issues](https://github.com/emanuelbesliu/homeassistant-colete/issues)
- [Documentație completă](README.md)
