# AI Countdown Studio

Streamlit-app voor een verticale countdownvideo van exact **62 seconden**:

- 1 seconde READY;
- daarna 60 tot en met 0, ieder cijfer precies één seconde;
- meerdere AI-personen;
- wisselende kleding en omgevingen;
- vaste instructie om strak in de camera te kijken;
- Kling Motion Control voor de losse scènes;
- lokale eindmontage met een exacte countdown;
- upload van rechtenvrije of correct gelicentieerde achtergrondmuziek.

## Starten

Start vanuit de hoofdmap van de repository:

    python -m streamlit run countdown_app/app.py

De bestaande KLING_API_KEY uit .env wordt automatisch gebruikt.

## Aanbevolen productie

Maak 7 clips van circa 10 seconden. Upload per scène een AI-character-afbeelding
en een rustige motion-reference waarin een persoon de hele tijd in de lens kijkt.
De app wisselt de clips rond 0, 10, 20, 30, 40, 50 en 60 seconden.

De cijfers worden niet door Kling gegenereerd: MoviePy plaatst ze tijdens de
eindmontage. Zo blijven de cijfers leesbaar en loopt 60 naar 0 exact synchroon.

## Muziekrechten

Een commerciële track of een soundalike die beschermd materiaal kopieert wordt
niet meegeleverd. Upload een eigen track waarvoor je publicatie- én
monetisatierechten hebt. Een energieke house-track van 124-128 BPM met build-up
en drops past goed bij dit format.

