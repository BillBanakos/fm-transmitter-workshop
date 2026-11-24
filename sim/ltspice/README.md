# LTspice

Put the LTspice schematics here (`.asc`, plus any `.lib`/`.asy` they need).

Suggested names:
- `fm_vco.asc` – Colpitts VCO + varactor modulator + ideal delay-line demodulator (verification)
- `fm_transmitter.asc` – full chain: VCO → PA → matching → LC low-pass → 50 Ω

`.raw` files are git-ignored; regenerate them headless with
`"C:\Program Files\ADI\LTspice\LTspice.exe" -b fm_vco.asc`.
Write µ as `u` in component values (e.g. `10u`) so the file survives encoding changes.
