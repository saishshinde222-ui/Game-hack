EMOTION_DESCRIPTIONS = {
    "vengeful": "Eyes burning with fury. The forge fire reflects in a face twisted by rage.",
    "fierce": "Battle-hardened gaze. Jaw clenched, ready to strike.",
    "serene": "Calm warmth radiates from peaceful eyes. A quiet strength.",
    "stoic": "Unmoved. Steady eyes that have seen a thousand battles.",
}


def analyze_seed_state(growth_log: dict) -> dict:
    """Convert a GrowthLog into prompts for Tripo (3D), Seedream (face), and emotion tags."""
    combat_style = growth_log.get("combatStyle", "balanced")
    anger = growth_log.get("angerEvents", 0)
    damage = growth_log.get("damageDealt", 0)
    time_in_sun = growth_log.get("timeInSun", 0)

    materials = {
        "fire-heavy": "molten obsidian with glowing fire runes",
        "ice": "crystalline ice with frost patterns",
        "lightning": "electrified steel with crackling energy",
        "shadow": "void-black metal with shadow tendrils",
        "holy": "radiant gold with divine engravings",
        "balanced": "forged steel with elemental inlays",
    }
    material = materials.get(combat_style, materials["balanced"])

    if anger > 5 or damage > 2000:
        emotion = "vengeful"
        mood = "aggressive, pulsing with rage"
    elif anger > 2 or damage > 1000:
        emotion = "fierce"
        mood = "intense, battle-hardened"
    elif time_in_sun > 5000:
        emotion = "serene"
        mood = "calm, radiating warmth"
    else:
        emotion = "stoic"
        mood = "steady, unwavering"

    element_colors = {
        "fire-heavy": "orange and red firelight",
        "ice": "cold blue frost glow",
        "lightning": "electric purple and white sparks",
        "shadow": "dark purple void energy",
        "holy": "warm golden divine light",
        "balanced": "neutral steel grey tones",
    }
    color_hint = element_colors.get(combat_style, "neutral tones")

    tripo_prompt = (
        f"Fantasy sword blade made of {material}, {mood}, "
        f"game-ready weapon, PBR textures, highly detailed"
    )

    face_prompt = (
        f"Close-up portrait of a fantasy warrior, {mood} expression, "
        f"face lit by {color_hint}, dramatic lighting, "
        f"detailed face, realistic skin, dark background, "
        f"cinematic, 4k, fantasy art style"
    )

    emotion_tags = [emotion, combat_style.replace("-", "_")]
    emotion_desc = EMOTION_DESCRIPTIONS.get(emotion, "")

    return {
        "tripo_prompt": tripo_prompt,
        "face_prompt": face_prompt,
        "emotion": emotion,
        "emotion_description": emotion_desc,
        "emotion_tags": emotion_tags,
        "icon_prompt": f"Game icon of a {material} sword, {mood}, dark background, centered",
    }
