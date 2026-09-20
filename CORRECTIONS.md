# Corrections — September 20, 2026

The September 3 data snapshot is retained; this is not a refreshed market report.

- Baltpool `type=spot&country=lt` is Lithuanian wood-chip SPOT. The official API documents `wood_pellets_spot` separately. The pellet endpoint returned 65.68 EUR/MWh for September 1 during this audit; it is not substituted into the older wood-chip history.
- DEPV describes delivered quantities of loose blown-in ENplus A1 pellets, not bags; prices include delivery within 50 km and incidental costs, excluding VAT.
- No subscriber alert was sent. Weekly subscriber delivery and automated alerts are not implemented. Paid ordering is paused.
- ENplus is a producer directory, not a verified buyer list. Comtrade figures are historical customs unit values, not purchase quotes. Sample destination rows are filtered to HS 440131.
- Snapshot inputs are pinned and hashed. The generator has no live DB dependency, does not refresh data and refuses modified inputs without explicit revalidation.
- EIA month-only storage, missing-value handling, source-country mappings and advertised historical depth still need a separate pipeline audit before paid delivery. Numeric reproducibility is not full source validation.
- The existing Enviva outreach restriction remains in force. No outreach or marketplace submissions are performed by this generator.

Sources: https://www.baltpool.eu/en/api-service/ ; https://www.baltpool.eu/wp-content/uploads/2026/06/baltpool-index-api-documentation.pdf ; https://www.depv.de/pelletpreis/

Build: `python3 gen_site.py` (requires pandas). This writes only the four HTML pages and corrected marketplace draft. Publishing is separate.
