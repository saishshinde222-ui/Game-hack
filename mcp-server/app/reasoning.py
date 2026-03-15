def analyze_seed_state(growth_log: dict) -> dict:
    """Convert a GrowthLog into prompts for Tripo (3D), SeeDance (2D), and Seedream (icon)."""
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

    tripo_prompt = (
        f"Fantasy sword blade made of {material}, {mood}, "
        f"game-ready weapon, PBR textures, highly detailed"
    )
    emotion_tags = [emotion, combat_style.replace("-", "_")]
    icon_prompt = f"Game icon of a {material} sword, {mood}, dark background, centered"

    return {
        "tripo_prompt": tripo_prompt,
        "emotion_tags": emotion_tags,
        "icon_prompt": icon_prompt,
        "needs_2d": True,
    }
