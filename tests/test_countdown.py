from countdown_app.core import TOTAL_SECONDS, countdown_value, default_scenes


def test_countdown_exact_boundaries():
    assert TOTAL_SECONDS == 62
    assert countdown_value(0.0) == "READY"
    assert countdown_value(0.999) == "READY"
    assert countdown_value(1.0) == "60"
    assert countdown_value(2.0) == "59"
    assert countdown_value(61.0) == "0"
    assert countdown_value(61.999) == "0"


def test_scene_prompts_force_camera_contact():
    scenes = default_scenes()
    assert len(scenes) == 7
    assert all("straight into the camera lens" in scene.prompt() for scene in scenes)


def test_cast_modes_keep_seven_landmark_scenes():
    for cast in ("Alleen vrouwen", "Alleen mannen", "Beide", "Non-binair en trans"):
        scenes = default_scenes(cast)
        assert len(scenes) == 7
        assert "Eiffel Tower" in scenes[0].environment
        assert "Statue of Liberty" in scenes[1].environment
        assert "Taj Mahal" in scenes[2].environment
        assert "Big Ben" in scenes[3].environment
