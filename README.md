# CS2 Market Channel

Daten-Videos über den CS2-Skin-Markt: ein langes Video plus Shorts pro Folge.

- `episode.json`: Folge und Datenstichtag (Zahlen in Grafik und Sprechtext passen so zusammen)
- `jobs/<name>/script.json`: Sprechtext pro Video (langes Video, Shorts)
- `pipeline/`: Daten, Analyse, Vertonung (ElevenLabs), Rendering
- Jeder Push auf `main` rendert alles neu. Ergebnisse landen im Branch `renders`.

Secrets: `ELEVENLABS_API_KEY`. Optional Variable `ELEVENLABS_VOICE_ID` (z. B. eigener Stimmklon).
