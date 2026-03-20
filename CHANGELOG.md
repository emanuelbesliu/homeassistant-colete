# Changelog

## [1.6.4] (2026-03-20)


### Bug Fixes

* fix Scanner Status sensor showing "Unknown" after HA restart — persist full coordinator data dict in storage and restore it on startup so all IMAP sensors retain their pre-restart values
* always save state after every successful scan (not only when new UIDs or AWBs appear) so persisted data stays current

### Enhancements

* AWBs Found sensor now exposes all discovered AWBs as extra state attributes (tracked_awbs, invalid_awbs, dismissed_awbs) grouped by status

## [1.6.3] (2026-03-20)


### Bug Fixes

* persist last scan timestamp in storage so the Last Scan sensor retains its value across HA restarts instead of showing "Unknown"

## [1.6.2] (2026-03-20)


### Bug Fixes

* fix track_parcel service not registered when IMAP entry loads before any parcel entry — service registration now happens for any entry type
* fix transient API errors (timeouts, network issues) permanently blacklisting valid AWBs as "invalid" — refactored to call ColeteAPI directly with three-way error handling (tracked/invalid/pending); only ColeteNotFoundError marks AWB as invalid, transient errors retry on next scan
* fix IMAP scan blocking HA startup — replaced async_config_entry_first_refresh() with async_set_updated_data() providing initial "waiting" state; first real scan deferred to normal schedule interval

## [1.6.1] (2026-03-20)


### Bug Fixes

* fix IMAP scanner performance: track ALL scanned UIDs (not just AWB-containing ones) to avoid re-downloading non-AWB emails on every scan cycle
* remove two-pass subject keyword filter that could miss AWBs in emails with generic subjects
* use BODY.PEEK[] instead of RFC822 to avoid setting \Seen flag on emails

## [1.6.0] (2026-03-20)


### Features

* add IMAP email scanner for automatic AWB detection from incoming emails
* keyword-based regex extraction (AWB, tracking, numar de urmarire, colet, expediere, livrare)
* courier sender domain hints (sameday.ro, fancourier.ro, cargus.ro, gls-romania.ro, dpd.ro)
* persistent deduplication of seen AWBs across restarts
* automatic parcel creation via colete.track_parcel service
* config flow menu: Track a Parcel / Set up Email Scanner
* IMAP options flow for scan interval, lookback days, folder
* 3 IMAP sensors: Scanner Status, Last Scan, AWBs Found
* translations for EN and RO

## [1.5.1](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.5.0...v1.5.1) (2026-03-19)


### Bug Fixes

* zero-pad DPD AWB to 14 digits to prevent API redirect ([aac9c1a](https://github.com/emanuelbesliu/homeassistant-colete/commit/aac9c1a520f1224f860f900b401a96401da04ff5))

## [1.5.0](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.4.0...v1.5.0) (2026-03-19)


### Features

* add DPD Romania courier support ([0835ad0](https://github.com/emanuelbesliu/homeassistant-colete/commit/0835ad01fa7f85c563de9fcdb9a2ba7ea4e0375f))

## [1.4.0](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.3.0...v1.4.0) (2026-03-18)


### Features

* add GLS Romania courier support ([5f8d5af](https://github.com/emanuelbesliu/homeassistant-colete/commit/5f8d5af4ff3d6fafb5c5050b1b20e59be2ba4ab4))

## [1.3.0](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.2.1...v1.3.0) (2026-03-18)


### Features

* add brand icons for integration ([689e9a5](https://github.com/emanuelbesliu/homeassistant-colete/commit/689e9a5fc843bb4ded92802da7fc52c8c51b4b0f))

## [1.2.1](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.2.0...v1.2.1) (2026-03-18)


### Bug Fixes

* remove manual config_entry assignment in OptionsFlow ([e23b20a](https://github.com/emanuelbesliu/homeassistant-colete/commit/e23b20aadcaa206a421f9e446b4ced054dd6e6dd))

## [1.2.0](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.1.0...v1.2.0) (2026-03-18)


### Features

* configurable retention_days for delivered parcels ([dae2e9c](https://github.com/emanuelbesliu/homeassistant-colete/commit/dae2e9c18e2266242a8e3ad21ae74982a9cf07cb))

## [1.1.0](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.0.2...v1.1.0) (2026-03-18)


### Features

* add Cargus courier support via HTML scraping ([6ac97b1](https://github.com/emanuelbesliu/homeassistant-colete/commit/6ac97b1d014de17487d609d6c5c932c8b0d099aa))


### Bug Fixes

* add beautifulsoup4 to CI import test dependencies ([77a6ffc](https://github.com/emanuelbesliu/homeassistant-colete/commit/77a6ffcd0b402b11cd34abd118d7e190e2893448))

## [1.0.2](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.0.1...v1.0.2) (2026-03-18)


### Bug Fixes

* rewrite FAN Courier parser for actual API response structure ([e591926](https://github.com/emanuelbesliu/homeassistant-colete/commit/e591926799671c2ae7f63c5cdf9bf1e3757642b8))

## [1.0.1](https://github.com/emanuelbesliu/homeassistant-colete/compare/v1.0.0...v1.0.1) (2026-03-17)


### Bug Fixes

* rewrite Sameday parser for actual API response structure ([d1ce4b1](https://github.com/emanuelbesliu/homeassistant-colete/commit/d1ce4b147d11206715d90d029bc0cc7f80874ff0))
