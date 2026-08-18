# Fitness Video Factory

**Versie: 0.3.0-clean-rebuild**

Lokale Streamlit-app voor een AI-fitnessworkflow met een vast character, echte motion-reference clips en automatische montage.

## Architectuur

- **Kling Motion Control**: full-body oefenbewegingen uit echte motion-reference video's.
- **Runway (optioneel)**: automatisch genereren van character-referenties A–E en AI voice-over.
- **MoviePy / FFmpeg**: normaliseren van motion-video's, timer/titel en eindmontage.

De app gebruikt bewust geen Runway Act-Two meer voor full-body fitnessbewegingen.

## Character set

- **A** — staand vooraanzicht
- **B** — staand ¾ aanzicht
- **C** — zijaanzicht
- **D** — op trainingsmat
- **E** — close-up gezicht

Je kunt A–E zelf uploaden. In dat geval is Runway niet nodig voor de character-afbeeldingen.

## Vereisten

- Windows, macOS of Linux
- Python 3.11 aanbevolen
- Kling API key voor Motion Control
- Optioneel: Runway API key voor A–E generatie en/of voice-over
- Echte motion-reference video's van 3–30 seconden

## Windows: snel starten

1. Download de repository via **Code → Download ZIP**.
2. Pak de ZIP uit naar een nieuwe lege map.
3. Maak in die map een nieuw bestand `.env` op basis van `.env.example`.
4. Vul je sleutels lokaal in:

```env
KLING_API_KEY=jouw_kling_api_key
RUNWAYML_API_SECRET=jouw_runway_api_key
```

Runway is optioneel als je A–E zelf uploadt en voice-over uit laat.

5. Dubbelklik op:

```text
start.bat
```

6. De app opent normaal op:

```text
http://localhost:8501
```

## Belangrijk over `.env` op Windows

Zet in Verkenner **Bestandsnaamextensies** aan. Het bestand moet exact `.env` heten, niet `.env.txt`.

Je echte `.env` staat in `.gitignore` en hoort nooit naar GitHub te worden gecommit.

## Workflow

### 1. Karakter

Upload één basisafbeelding en genereer A–E via Runway, of upload A–E handmatig.

### 2. Training

Per oefening:

- geef de oefening een naam;
- upload één motion-reference video;
- kies AUTO/A/B/C/D/E;
- pas eventueel de voice-overtekst aan.

De app normaliseert de motion-video lokaal naar een compacte 9:16 MP4.

### 3. Maak video

De pipeline:

```text
character reference
      +
motion reference
      ↓
Kling Motion Control
      ↓
AI fitnessclip
      ↓
optionele Runway voice-over
      ↓
timer + titel
      ↓
finale MP4
```

## Motion-reference richtlijnen

Voor de beste fitnessresultaten:

- één persoon in beeld;
- volledig lichaam en hoofd zichtbaar;
- voeten niet afsnijden;
- één continue opname;
- geen cuts;
- liefst geen bewegende camera;
- rustige tot gematigde bewegingssnelheid;
- 3–30 seconden per clip.

Gebruik een technisch correcte uitvoering als referentie. De AI moet de beweging volgen, niet zelf de oefentechniek bedenken.

## Lokale projectdata

Per project wordt lokaal aangemaakt:

```text
projects/<projectnaam>/
├─ uploads/
├─ references/
├─ motions/
├─ clips/
├─ audio/
├─ output/
└─ workout.json
```

`projects/*` wordt niet naar GitHub gestuurd.

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
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Docker

```bash
cp .env.example .env
# vul de lokale .env in
docker compose up --build
```

Open vervolgens `http://localhost:8501`.

## Testen

```bash
pytest -q
```

## Problemen oplossen

### App start niet

Start `start.bat` opnieuw. Het venster blijft open en toont de foutmelding.

### `app.py` is 0 KB na handmatig kopiëren

Download de complete ZIP opnieuw naar een **nieuwe lege map** in plaats van losse bestanden te kopiëren.

### `.env` wordt niet gelezen

Controleer dat het bestand echt `.env` heet en niet `.env.txt`.

### Kling weigert de aanvraag

De app toont HTTP-status, Kling-code en foutreden. Kopieer alleen die foutmelding voor diagnose; deel nooit je API-key.

## Privacy en rechten

Gebruik alleen character-beelden, stemopnames en motion-reference video's waarvoor je toestemming of gebruiksrechten hebt. API-keys blijven lokaal in `.env`.
