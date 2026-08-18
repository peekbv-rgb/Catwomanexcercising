from __future__ import annotations

BASE_STYLE = """Photorealistic AI fitness model reference of the exact same woman from @subject.
Preserve facial identity, long dark-brown hair, defined eyebrows, natural makeup, skin tone,
smaller natural-looking lips, and the same overall body proportions. She has an athletic but
natural feminine physique. Outfit must stay identical in every reference: fitted charcoal-grey
fitness crop top, high-waisted black leggings, clean white training shoes. Environment must stay
identical: modern premium fitness studio, neutral gray walls, dark rubber floor, subtle black
fitness equipment, soft realistic studio lighting. Realistic anatomy, realistic hands and feet,
no text, no logos, no jewelry, no exaggerated muscles or proportions."""

REFERENCE_PROMPTS = {
    "A": BASE_STYLE + """

Create a clean full-body FRONT VIEW. She stands upright facing the camera, head to toe fully visible,
feet shoulder-width apart, arms relaxed naturally by her sides and slightly separated from the torso.
Centered vertical composition with ample empty space around the entire body. This is a neutral master
character reference, not an action pose.""",
    "B": BASE_STYLE + """

Create a clean full-body THREE-QUARTER VIEW, body rotated about 45 degrees while the face remains
recognizable. Head to toe fully visible, relaxed upright stance, arms down naturally, both shoes visible.
Keep the same gym, outfit, lighting, hairstyle and proportions as @subject.""",
    "C": BASE_STYLE + """

Create a clean full-body SIDE PROFILE VIEW. She stands upright in strict side profile with natural
posture, arms resting by her sides, head to toe fully visible, both feet visible. Keep the same gym,
outfit, lighting, hairstyle and proportions as @subject.""",
    "D": BASE_STYLE + """

Create a full-body FLOOR REFERENCE on a black exercise mat. She lies on her back in a neutral glute-bridge
start position: knees bent, feet flat on the mat, arms alongside the torso, entire body visible, face clearly
recognizable. Slightly elevated camera angle. Keep the same gym, outfit, lighting and identity as @subject.""",
    "E": BASE_STYLE + """

Create a CLOSE-UP FACE REFERENCE from chest up. Preserve the face very faithfully: eye shape, eyebrows,
long dark-brown hair, skin tone, natural makeup and smaller natural lips. Calm confident expression,
looking toward camera. Same charcoal-grey fitness top and softly blurred version of the same gym background.""",
}

EXERCISE_CUES = {
    "squat": "Squats. Houd je borst rustig omhoog, knieën in lijn met je voeten en beweeg gecontroleerd.",
    "reverse lunge": "Reverse lunges. Stap rustig naar achteren, blijf stabiel en duw gecontroleerd terug omhoog.",
    "lunge": "Lunges. Houd je romp stabiel en je voorste knie in lijn met je voet.",
    "romanian deadlift": "Romanian deadlift. Duw je heupen naar achteren, houd je rug neutraal en beweeg gecontroleerd.",
    "rdl": "Romanian deadlift. Duw je heupen naar achteren, houd je rug neutraal en beweeg gecontroleerd.",
    "shoulder press": "Shoulder press. Houd je romp stabiel en druk de gewichten rustig boven je hoofd.",
    "bent-over row": "Bent-over row. Houd je rug neutraal en trek je ellebogen gecontroleerd naar achteren.",
    "row": "Row. Houd je romp stabiel en trek gecontroleerd vanuit je rug.",
    "glute bridge": "Glute bridge. Duw vanuit je hielen en span je bilspieren bovenaan kort aan.",
    "mountain climber": "Mountain climbers. Houd je schouders stabiel en wissel de knieën ritmisch af.",
    "plank": "Plank. Maak één rechte lijn van schouders tot hielen en houd je romp actief.",
}


def cue_for_exercise(name: str) -> str:
    key = name.strip().lower()
    for needle, cue in EXERCISE_CUES.items():
        if needle in key:
            return cue
    return f"{name}. Beweeg rustig en gecontroleerd en houd je techniek netjes."


def auto_reference_slot(exercise_name: str) -> str:
    key = exercise_name.lower()
    if any(word in key for word in ("glute", "bridge", "plank", "mountain", "floor", "mat")):
        return "D"
    if any(word in key for word in ("rdl", "deadlift", "hinge")):
        return "C"
    if any(word in key for word in ("lunge", "row")):
        return "B"
    return "A"
