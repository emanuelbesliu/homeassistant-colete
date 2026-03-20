# Changelog

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
