from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from core.media import compress_motion_reference, render_final_video
from core.prompts import auto_reference_slot, cue_for_exercise
from core.runway_client import FitnessRunwayClient
from core.utils import ensure_dir, slugify
from core.workout import Exercise, validate_exercises

load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = ensure_dir(APP_ROOT / "projects")

st.set_page_config(page_title="Fitness Video Factory", page_icon="🏋️", layout="wide")


def get_project_dir(project_name: str) -> Path:
    key = slugify(project_name or "fitness-project")
    p = ensure_dir(PROJECTS_DIR / key)
    for sub in ("uploads", "references", "motions", "clips", "audio", "output"):
        ensure_dir(p / sub)
    return p


def save_upload(upload, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(upload.getbuffer())
    return path


def status_callback(container):
    def cb(message: str):
        container.info(message)
    return cb


st.title("🏋️ Fitness Video Factory")
st.caption("Van één AI-personage + echte motion-reference clips naar een gemonteerde verticale fitnessvideo.")

with st.sidebar:
    st.header("Instellingen")
    project_name = st.text_input("Projectnaam", value="AI Fitness Coach")
    api_key = st.text_input(
        "Runway API key",
        value=os.getenv("RUNWAYML_API_SECRET", ""),
        type="password",
        help="Wordt alleen in deze sessie gebruikt. Sla hem desgewenst lokaal op in .env.",
    )
    st.markdown("---")
    st.caption("Gebruik alleen beelden, stemmen en motion-reference video's waarvoor je toestemming/rechten hebt.")

project_dir = get_project_dir(project_name)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

character_tab, workout_tab, render_tab = st.tabs(["1. Character", "2. Workout", "3. Maak video"])

with character_tab:
    st.subheader("Character reference set A–E")
    st.write("Upload één basisafbeelding en laat A–E automatisch maken, óf upload je eigen A–E referenties.")

    seed_upload = st.file_uploader("Basisafbeelding / identity seed", type=["png", "jpg", "jpeg", "webp"], key="seed")
    seed_path = project_dir / "uploads" / "identity_seed.png"
    if seed_upload is not None:
        seed_path = save_upload(seed_upload, seed_path)
        st.image(str(seed_path), width=260, caption="Identity seed")
    elif seed_path.exists():
        st.image(str(seed_path), width=260, caption="Identity seed (opgeslagen)")

    st.markdown("### Eigen referenties uploaden")
    cols = st.columns(5)
    for idx, slot in enumerate("ABCDE"):
        with cols[idx]:
            up = st.file_uploader(f"{slot}", type=["png", "jpg", "jpeg", "webp"], key=f"ref_{slot}")
            ref_path = project_dir / "references" / f"reference_{slot}.png"
            if up is not None:
                save_upload(up, ref_path)
            if ref_path.exists():
                st.image(str(ref_path), use_container_width=True, caption=slot)
            else:
                st.caption(f"{slot}: nog niet aanwezig")

    c1, c2 = st.columns([1, 2])
    with c1:
        generate_refs = st.button("✨ Genereer ontbrekende A–E", type="primary")
    with c2:
        st.caption("A = vooraanzicht · B = ¾ · C = zijaanzicht · D = mat · E = close-up")

    if generate_refs:
        if not api_key:
            st.error("Vul eerst je Runway API key in.")
        elif not seed_path.exists():
            st.error("Upload eerst een basisafbeelding.")
        else:
            run = FitnessRunwayClient(api_key)
            status = st.empty()
            cb = status_callback(status)
            try:
                a_path = project_dir / "references" / "reference_A.png"
                if not a_path.exists():
                    a_path = run.generate_reference("A", [seed_path], project_dir / "references", cb)
                for slot in "BCDE":
                    out = project_dir / "references" / f"reference_{slot}.png"
                    if out.exists():
                        continue
                    run.generate_reference(slot, [a_path, seed_path], project_dir / "references", cb)
                status.success("A–E referenties zijn klaar.")
                st.rerun()
            except Exception as exc:
                status.error(f"Genereren mislukt: {exc}")

with workout_tab:
    st.subheader("Workout samenstellen")
    st.info("Gebruik echte, technisch correcte motion-reference clips van 3–30 seconden. Het model neemt die beweging over.")
    default_names = [
        "Squats",
        "Reverse lunges",
        "Romanian deadlift",
        "Shoulder press",
        "Bent-over row",
        "Glute bridge",
        "Mountain climbers",
    ]
    count = st.number_input("Aantal oefeningen", min_value=1, max_value=12, value=7, step=1)

    exercise_specs: list[dict] = []
    for i in range(int(count)):
        st.markdown(f"#### {i + 1}. Oefening")
        left, mid, right = st.columns([2.2, 1, 2.8])
        default_name = default_names[i] if i < len(default_names) else f"Oefening {i + 1}"
        with left:
            name = st.text_input("Naam", value=default_name, key=f"name_{i}")
            auto_slot = auto_reference_slot(name)
            ref_choice = st.selectbox(
                "Character reference",
                ["AUTO", "A", "B", "C", "D", "E"],
                index=0,
                key=f"slot_{i}",
                help=f"AUTO kiest nu {auto_slot} voor deze naam.",
            )
        with mid:
            motion = st.file_uploader("Motion video", type=["mp4", "mov", "m4v"], key=f"motion_{i}")
            existing_motion = project_dir / "motions" / f"{i+1:02d}_{slugify(name)}.mp4"
            if motion is not None:
                raw_path = project_dir / "uploads" / f"motion_raw_{i+1:02d}{Path(motion.name).suffix.lower()}"
                save_upload(motion, raw_path)
                try:
                    compress_motion_reference(raw_path, existing_motion)
                    st.success("Klaar")
                except Exception as exc:
                    st.error(str(exc))
            elif existing_motion.exists():
                st.caption("✓ motion opgeslagen")
        with right:
            voice = st.text_area("Voice-over", value=cue_for_exercise(name), key=f"voice_{i}", height=95)

        exercise_specs.append(
            {
                "name": name,
                "reference_slot": auto_slot if ref_choice == "AUTO" else ref_choice,
                "motion_path": str(existing_motion),
                "voiceover": voice,
            }
        )

    if st.button("💾 Sla workout op"):
        config = {"project": project_name, "exercises": exercise_specs}
        (project_dir / "workout.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        st.success("Workout opgeslagen.")

with render_tab:
    st.subheader("Eén knop → complete fitnessvideo")
    voice_enabled = st.checkbox("AI voice-over toevoegen", value=True)
    voice_ref_upload = st.file_uploader(
        "Optioneel: eigen stemreferentie (audio)",
        type=["mp3", "wav", "m4a"],
        help="Alleen gebruiken met toestemming van de stem-eigenaar.",
    )
    voice_ref_path = None
    if voice_ref_upload is not None:
        voice_ref_path = save_upload(
            voice_ref_upload,
            project_dir / "uploads" / f"voice_reference{Path(voice_ref_upload.name).suffix.lower()}",
        )

    workout_path = project_dir / "workout.json"
    if workout_path.exists():
        stored = json.loads(workout_path.read_text(encoding="utf-8"))
        exercise_specs = stored.get("exercises", exercise_specs)
    else:
        st.warning("Sla eerst de workout op in tab 2. Je kunt ook direct renderen met de huidige invoer.")

    st.markdown("**Pipeline:** refs controleren → motions comprimeren → Act-Two per oefening → voice-over → timer/titel → MP4")
    make_video = st.button("🎬 MAAK COMPLETE VIDEO", type="primary", use_container_width=True)

    if make_video:
        if not api_key:
            st.error("Vul eerst je Runway API key in.")
            st.stop()

        exercises = [Exercise(**spec).normalized() for spec in exercise_specs]
        errors = validate_exercises(exercises)
        refs_missing = [
            slot
            for slot in {ex.reference_slot for ex in exercises}
            if not (project_dir / "references" / f"reference_{slot}.png").exists()
        ]
        if refs_missing:
            errors.append("Ontbrekende character references: " + ", ".join(sorted(refs_missing)))
        if errors:
            for error in errors:
                st.error(error)
            st.stop()

        run = FitnessRunwayClient(api_key)
        status = st.empty()
        progress = st.progress(0.0)
        cb = status_callback(status)
        render_items = []

        try:
            total_steps = len(exercises) * (2 if voice_enabled else 1) + 1
            done = 0
            for idx, ex in enumerate(exercises, start=1):
                ref_path = project_dir / "references" / f"reference_{ex.reference_slot}.png"
                motion_path = Path(ex.motion_path)
                clip_path = project_dir / "clips" / f"{idx:02d}_{ex.slug}.mp4"
                audio_path = project_dir / "audio" / f"{idx:02d}_{ex.slug}.mp3"

                if not clip_path.exists():
                    run.generate_character_performance(ref_path, motion_path, clip_path, progress=cb)
                done += 1
                progress.progress(done / total_steps)

                audio_for_render = None
                if voice_enabled:
                    if not audio_path.exists():
                        run.generate_tts(ex.voiceover, audio_path, voice_reference=voice_ref_path, progress=cb)
                    audio_for_render = audio_path
                    done += 1
                    progress.progress(done / total_steps)

                render_items.append((clip_path, ex.name, audio_for_render))

            output = project_dir / "output" / "fitness_workout_final.mp4"
            cb("Finale video monteren…")
            render_final_video(render_items, output, progress=cb)
            progress.progress(1.0)
            status.success("Klaar — je fitnessvideo is gerenderd.")
            st.video(str(output))
            st.download_button(
                "⬇️ Download MP4",
                data=output.read_bytes(),
                file_name=f"{slugify(project_name)}.mp4",
                mime="video/mp4",
                use_container_width=True,
            )
        except Exception as exc:
            status.error(f"Pipeline gestopt: {exc}")
            st.exception(exc)

st.markdown("---")
st.caption("Fitness Video Factory · lokale projectbestanden blijven in de map projects/. API-generaties kosten Runway-credits.")
