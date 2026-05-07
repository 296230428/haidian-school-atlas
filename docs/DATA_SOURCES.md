# Data Sources

This project combines local spreadsheet inputs, public web pages, OCR outputs and map/geocoding data.

## Derived Data

- `outputs/ranking_data/ranking_rows.json`: normalized school ranking rows.
- `outputs/ranking_data/address_regions.json`: address-region classification rows.
- `outputs/map/primary_school_geocodes.json`: geocoding results used by static and interactive maps.
- `outputs/school_district/data/school_district_dataset.json`: school district, community and rental/evaluation fields.

## Generated Artifacts

- `.xlsx` files under `outputs/ranking_data/` and `outputs/school_district/` are generated from the JSON datasets.
- `outputs/interactive_map/海淀小学互动地图.html` is a local static map page that does not require AMap credentials.
- `outputs/amap_map/海淀小学高德互动地图.html` is generated locally and may contain AMap credentials. It is ignored by Git.

## Publication Policy

The repository is intended to publish source code, derived JSON data and reproducible generation scripts. Raw cached webpages, downloaded admission images and OCR intermediate files are ignored by default because they may contain third-party content.

Before publishing a release, review the derived data for:

- OCR mistakes
- stale source pages
- mismatched school names
- approximate geocoding points
- missing rental/evaluation attribution

For formal use, verify every school district and community match against official education authority publications.
