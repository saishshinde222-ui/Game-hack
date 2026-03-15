import asyncio
import logging
import uuid
from pathlib import Path

from app.clients.tripo import TripoClient
from app.clients.seedream import SeedreamClient
from app.reasoning import analyze_seed_state

logger = logging.getLogger(__name__)

WEAPON_WORDS = [
    "sword", "blade", "axe", "hammer", "dagger", "spear", "staff", "bow",
    "shield", "mace", "weapon", "knife", "katana", "scythe", "wand",
]

FORGE_WORDS = ["forge", "generate", "make", "create", "craft", "build"]

OBJECT_3D_WORDS = [
    "tree", "rock", "house", "castle", "chair", "table", "chest",
    "barrel", "lamp", "statue", "pillar", "fountain", "bridge",
    "tower", "gate", "wall", "fence", "bench", "torch", "throne",
]


async def handle_user_prompt(prompt: str, context: dict, assets_dir: Path) -> list[dict]:
    prompt_lower = prompt.lower().strip()

    if _is_remove_request(prompt_lower):
        return _remove_entity(prompt)

    if _is_behavior_request(prompt_lower):
        return _attach_behavior(prompt)

    if _has_weapon_word(prompt_lower):
        return await _forge_weapon_with_emotion(prompt, assets_dir)

    if _needs_3d_generation(prompt_lower):
        return await _generate_3d_object(prompt, assets_dir)

    if _is_spawn_request(prompt_lower):
        return await _generate_3d_object(prompt, assets_dir)

    return [{"type": "status", "message": "Command not recognized: %s" % prompt}]


def _has_weapon_word(p: str) -> bool:
    return any(w in p for w in WEAPON_WORDS)


def _needs_3d_generation(p: str) -> bool:
    has_object = any(w in p for w in OBJECT_3D_WORDS)
    has_action = any(w in p for w in FORGE_WORDS + ["add", "spawn", "place"])
    return has_object and has_action


def _is_spawn_request(p: str) -> bool:
    return any(w in p for w in ["add", "spawn", "create", "place", "make", "generate", "build"])


def _is_remove_request(p: str) -> bool:
    return any(w in p for w in ["remove", "delete", "destroy"])


def _is_behavior_request(p: str) -> bool:
    return any(w in p for w in ["wander", "move to", "chop", "equip"])


async def _forge_weapon_with_emotion(prompt: str, assets_dir: Path) -> list[dict]:
    """Full pipeline: Reasoning → parallel Tripo (weapon) + Seedream (face emotion) → spawn + portrait."""
    seed_id = str(uuid.uuid4())[:8]
    growth_log = _extract_growth_log(prompt)
    prompts = analyze_seed_state(growth_log)

    commands = []

    # --- Parallel: Tripo weapon + Seedream emotion face ---
    commands.append({
        "type": "status",
        "message": "Forging weapon + generating emotion... (%s)" % prompts["emotion"].upper(),
    })

    tripo_task = _run_tripo(prompts["tripo_prompt"], assets_dir, seed_id)
    face_task = _run_seedream_face(prompts["face_prompt"], assets_dir, seed_id)

    results = await asyncio.gather(tripo_task, face_task, return_exceptions=True)

    glb_path, thumb_path = (None, None)
    face_path = None

    if not isinstance(results[0], Exception):
        glb_path, thumb_path = results[0]
    else:
        logger.error("Tripo failed: %s", results[0])
        commands.append({"type": "status", "message": "Weapon generation failed: %s" % results[0]})

    if not isinstance(results[1], Exception):
        face_path = results[1]
    else:
        logger.error("Face generation failed: %s", results[1])

    # --- Send portrait update ---
    if face_path and face_path.exists():
        commands.append({
            "type": "update_portrait",
            "image_url": "/assets/%s_face.png" % seed_id,
            "emotion": prompts["emotion"],
            "description": prompts["emotion_description"],
        })

    # --- Spawn weapon ---
    if glb_path and glb_path.exists():
        entity_id = "weapon_%s" % seed_id
        commands.append({
            "type": "spawn_entity",
            "id": entity_id,
            "model_path": str(glb_path),
            "position": {"x": 0, "y": 1, "z": -2},
            "rotation": {"x": 0, "y": 0, "z": 0},
            "scale": {"x": 1, "y": 1, "z": 1},
            "scripts": ["equippable"],
        })
        commands.append({
            "type": "status",
            "message": "Weapon forged! Emotion: %s" % prompts["emotion"].upper(),
        })
    elif not any(isinstance(r, Exception) for r in results[:1]):
        commands.append({"type": "status", "message": "Forge complete but no model generated"})

    return commands


async def _run_tripo(prompt: str, assets_dir: Path, seed_id: str):
    tripo = TripoClient()
    return await tripo.generate(prompt=prompt, output_dir=assets_dir, seed_id=seed_id)


async def _run_seedream_face(face_prompt: str, assets_dir: Path, seed_id: str):
    seedream = SeedreamClient()
    return await seedream.generate_face(
        prompt=face_prompt, output_dir=assets_dir, seed_id=seed_id
    )


async def _generate_3d_object(prompt: str, assets_dir: Path) -> list[dict]:
    """Generate a generic 3D object via Tripo."""
    seed_id = str(uuid.uuid4())[:8]
    tripo_prompt = _build_object_prompt(prompt)

    commands = []
    commands.append({"type": "status", "message": "Generating 3D: %s" % tripo_prompt[:80]})

    try:
        glb_path, _ = await _run_tripo(tripo_prompt, assets_dir, seed_id)
        entity_id = _extract_entity_name(prompt) + "_%s" % seed_id

        commands.append({
            "type": "spawn_entity",
            "id": entity_id,
            "model_path": str(glb_path) if glb_path else "",
            "position": {"x": 0, "y": 1, "z": -2},
            "scale": {"x": 1, "y": 1, "z": 1},
            "scripts": [],
        })
        commands.append({"type": "status", "message": "Done! Spawned: %s" % entity_id})

    except Exception as e:
        logger.exception("3D generation failed")
        commands.append({"type": "status", "message": "Generation failed: %s" % str(e)})

    return commands


def _build_object_prompt(prompt: str) -> str:
    clean = prompt.strip()
    for skip in ["add", "spawn", "create", "place", "make", "generate", "build", "a", "an", "the"]:
        clean = clean.replace(skip, "", 1).strip()
    return "3D game asset: %s, stylized, PBR textures, detailed, game-ready" % clean


def _extract_entity_name(prompt: str) -> str:
    words = prompt.lower().split()
    for skip in ["add", "spawn", "create", "place", "make", "generate", "build",
                  "forge", "craft", "a", "an", "the", "me", "for", "with"]:
        words = [w for w in words if w != skip]
    return "_".join(words[:3]) if words else "entity"


def _extract_growth_log(prompt: str) -> dict:
    p = prompt.lower()
    style = "balanced"
    for s in ["fire", "ice", "lightning", "shadow", "holy"]:
        if s in p:
            style = "fire-heavy" if s == "fire" else s
            break

    anger = 5 if any(w in p for w in ["angry", "rage", "vengeful", "fury"]) else 1
    damage = 2000 if any(w in p for w in ["powerful", "strong", "deadly"]) else 800

    return {
        "combatStyle": style,
        "timeInSun": 0,
        "angerEvents": anger,
        "damageDealt": damage,
    }


def _remove_entity(prompt: str) -> list[dict]:
    words = prompt.lower().split()
    for skip in ["remove", "delete", "destroy", "the", "a", "an"]:
        words = [w for w in words if w != skip]
    if not words:
        return [{"type": "status", "message": "Remove what?"}]
    return [{"type": "remove_entity", "id": "_".join(words)}]


def _attach_behavior(prompt: str) -> list[dict]:
    p = prompt.lower()
    behavior = None
    for b in ["wander", "move_to", "choppable", "equippable"]:
        if b.replace("_", " ") in p or b in p:
            behavior = b
            break
    if behavior is None:
        return [{"type": "status", "message": "Unknown behavior: %s" % prompt}]
    return [{
        "type": "attach_behavior",
        "entity_id": "",
        "behavior": behavior,
        "params": {},
    }, {"type": "status", "message": "Specify entity_id for '%s'" % behavior}]
