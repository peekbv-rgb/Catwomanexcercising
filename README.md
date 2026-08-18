# Fitness Video Factory

Lokale Streamlit-webapp om van één AI-personage + echte motion-reference clips een complete verticale fitnessvideo te maken.

## Wat de tool automatiseert

1. **Character references A–E** maken vanuit één basisafbeelding via Runway `gpt_image_2` (optioneel).
2. Per oefening een passende character-reference kiezen:
   - A = staand vooraanzicht
   - B = staand ¾ aanzicht
   - C = zijaanzicht
   - D = op trainingsmat
   - E = close-up gezicht
3. Motion-reference video normaliseren naar een compacte verticale MP4.
4. **Kling VIDEO 3.0 Motion Control** gebruiken voor full-body bewegingsoverdracht.
5. Optionele Nederlandse **AI voice-over** via Runway Seed Audio.
6. Automatisch oefeningstitel + countdown toevoegen.
7. Alle oefenclips monteren naar één MP4.

> Gebruik voor fitnessbewegingen echte, technisch correcte motion-reference clips. Controleer gegenereerde oefentechniek altijd vóór publicatie.

## Benodigd

- Windows, macOS of Linux
- Python 3.11 aanbevolen
- **Kling Open Platform API key + credits** voor Motion Control
- Optioneel: **Runway API key + credits** voor A–E generatie en/of voice-over
- Motion-reference clips van 3–30 seconden

## Snel starten op Windows

1. Clone/download deze repository.
2. Kopieer `.env.example` naar `.env`.
3. Vul je sleutels uitsluitend in je **lokale** `.env` in:

```env
KLING_API_KEY=jouw_kling_api_key
RUNWAYML_API_SECRET=jouw_runway_api_key
```

`RUNWAYML_API_SECRET` mag leeg blijven als je bestaande A–E afbeeldingen gebruikt en AI voice-over uitzet.

4. Dubbelklik op `start.bat`.
5. De browser opent normaal op `http://localhost:8501`.

**Commit `.env` nooit naar GitHub.** Het bestand staat in `.gitignore`.

## Handmatig starten

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Daarna:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Workflow

### 1. Karakter

Upload je eigen A–E referenties, of upload één identity seed en laat de app ontbrekende A–E beelden via Runway maken.

### 2. Training

Vul per oefening in:

- naam
- motion-reference video
- character reference (AUTO/A/B/C/D/E)
- voice-over tekst

Sla daarna de workout op.

### 3. Maak video

Kies links:

- **Kling kwaliteit**: Standard of Professional
- **Kling oriëntatie**: voor fitness meestal `Volg motion-video`
- AI voice-over aan/uit

Klik daarna **MAAK COMPLETE VIDEO**.

De pipeline is:

```text
character refs
→ motion-reference
→ Kling 3.0 Motion Control
→ optionele Runway voice-over
→ timer + titel
→ finale MP4
```

## Projectmappen

Elke projectnaam krijgt lokaal een map onder:

```text
projects/<projectnaam>/
```

met:

```text
uploads/       originele uploads
references/    A–E character images
motions/       genormaliseerde motion references
clips/         Kling Motion Control clips
audio/         gegenereerde voice-overs
output/        uiteindelijke MP4
```

Projectdata wordt door `.gitignore` niet naar GitHub gestuurd.

## Techniek

- UI: Streamlit
- Full-body motion: Kling VIDEO 3.0 Motion Control API
- Character reference generation: Runway `gpt_image_2`
- Voice-over: Runway `seed_audio`
- Video preprocessing: `imageio-ffmpeg`
- Montage/overlays: MoviePy + Pillow

## Motion-reference richtlijnen

Voor de beste fitnessresultaten:

- één persoon in beeld
- volledige persoon en hoofd zichtbaar
- één doorlopende opname zonder cuts
- camera liefst stil
- beweging op rustig/matig tempo
- full-body character-afbeelding combineren met full-body motion-video
- 3–30 seconden wanneer de oriëntatie de motion-video volgt

## Eerste test

Test eerst met **één oefening van 3–5 seconden** in Kling Standard. Zo controleer je de hele keten met zo weinig mogelijk credits voordat je een complete workout rendert.

## Veiligheid en rechten

Gebruik alleen afbeeldingen, stemmen en videoreferenties waarvoor je toestemming/gebruiksrechten hebt. Bij fitnesscontent blijft menselijke controle op correcte oefentechniek noodzakelijk.
