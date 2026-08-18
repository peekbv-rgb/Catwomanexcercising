# Fitness Video Factory

Een lokale Streamlit-webapp waarmee je van één AI-personage en echte motion-reference clips een complete verticale fitnessvideo maakt.

## Wat de tool automatiseert

1. **Character references A–E** genereren vanuit één basisafbeelding via Runway `gpt_image_2`.
2. Per oefening automatisch een passende referentie kiezen:
   - A = staand vooraanzicht
   - B = staand ¾ aanzicht
   - C = zijaanzicht
   - D = op trainingsmat
   - E = close-up gezicht
3. Motion-reference video normaliseren/comprimeren naar een compacte 9:16 MP4.
4. **Act-Two body control** uitvoeren via Runway om de beweging op het AI-personage over te brengen.
5. Optionele Nederlandse **AI voice-over** via Runway Seed Audio.
6. Automatisch oefeningstitel + countdown in beeld zetten.
7. Alle clips achter elkaar monteren naar één MP4.

> Belangrijk: gebruik voor fitnessbewegingen echte, technisch correcte motion-reference clips. Laat een generatief model niet zelf de oefentechniek verzinnen.

## Benodigd

- Windows, macOS of Linux
- Python 3.11 aanbevolen
- Runway developer-account + API key + credits
- Motion-reference clips van 3–30 seconden
- Beelden/stemmen/video's waarvoor je toestemming of gebruiksrechten hebt

## Snel starten op Windows

1. Clone deze repository.
2. Kopieer `.env.example` naar `.env`.
3. Vul je Runway API key in:

```env
RUNWAYML_API_SECRET=rw_...
```

4. Dubbelklik op:

```text
start.bat
```

5. De browser opent normaal op `http://localhost:8501`.

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

## Docker

```bash
cp .env.example .env
# vul de API key in .env
docker compose up --build
```

Open daarna `http://localhost:8501`.

## Workflow in de app

### 1. Character

Upload één identity seed. Klik **Genereer ontbrekende A–E**. Je kunt A–E ook zelf uploaden als je al goede referenties hebt.

### 2. Workout

Vul per oefening in:

- naam
- motion-reference video
- character reference (AUTO/A/B/C/D/E)
- voice-over tekst

Sla de workout op.

### 3. Maak video

Klik **MAAK COMPLETE VIDEO**.

De app genereert ontbrekende oefenclips, maakt optioneel voice-over en rendert daarna de complete video.

## Projectmappen

Elke projectnaam krijgt een lokale map onder:

```text
projects/<projectnaam>/
```

Daarin staan:

```text
uploads/       originele uploads
references/    A–E character images
motions/       gecomprimeerde motion references
clips/         gegenereerde Act-Two clips
audio/         gegenereerde voice-overs
output/        uiteindelijke MP4
```

Deze projectdata wordt door `.gitignore` niet naar GitHub gestuurd.

## Technische keuzes

- UI: Streamlit
- AI image/video/audio: officiële Runway Python SDK
- Character motion: `character_performance` / `act_two`
- Image references: `gpt_image_2`
- Voice-over: `seed_audio`
- Video preprocessing: `imageio-ffmpeg`
- Montage/overlays: MoviePy + Pillow

## Beperkingen van deze eerste versie

- De tool maakt bewust **geen eigen fitnessbewegingen uit tekst**. Voor betrouwbare techniek moet je motion-reference video aanleveren.
- Voor zeer lange workouts worden veel losse AI-clips gegenereerd; dit kan behoorlijk wat API-credits kosten.
- Generatieve video blijft probabilistisch. Controleer handen, voeten, gewichten en oefentechniek voor publicatie.
- De tool uploadt projecten niet automatisch naar cloudopslag en publiceert niet automatisch op YouTube/TikTok/Instagram.

## Testen

```bash
pip install pytest
pytest -q
```

## Veiligheid en rechten

Gebruik alleen afbeeldingen van personen, stemopnames en videoreferenties die je mag gebruiken. Bij fitnesscontent blijft menselijke controle op correcte oefentechniek noodzakelijk.
