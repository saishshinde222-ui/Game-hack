import asyncio
import logging
from pathlib import Path

from app.clients.tripo import TripoClient
from app.clients.seedream import SeedreamClient
from app.reasoning import analyze_seed_state

logger = logging.getLogger(__name__)


async def handle_user_prompt(prompt: str, context: dict, assets_dir: Path) -> list[dict]:
    """
    Takes a user prompt + project context from Godot.
    Returns a list of JSON commands to send back to Godot.
    """
    prompt_lower = prompt.lower().strip()

    if _is_forge_request(prompt_lower):
        return await _forge_weapon(prompt, assets_dir)

    if _is_spawn_request(prompt_lower):
        return _spawn_placeholder(prompt)

    if _is_remove_request(prompt_lower):
        return _remove_entity(prompt)

    if _is_behavior_request(prompt_lower):
        return _attach_behavior(prompt)

    return [{"type": "status", "message": "Command not recognized: %s" % prompt}]


def _is_forge_request(p: str) -> bool:
    return any(w in p for w in ["forge", "generate weapon", "create sword", "make blade", "make weapon"])


def _is_spawn_request(p: str) -> bool:
    return any(w in p for w in ["add", "spawn", "create", "place"])


def _is_remove_request(p: str) -> bool:
    return any(w in p for w in ["remove", "delete", "destroy"])


def _is_behavior_request(p: str) -> bool:
    return any(w in p for w in ["wander", "move to", "chop", "equip"])


async def _forge_weapon(prompt: str, assets_dir: Path) -> list[dict]:
    """Full AI forge pipeline: reasoning → Tripo 3D → spawn command."""
    growth_log = _extract_growth_log(prompt)
    prompts = analyze_seed_state(growth_log)

    commands = []
    commands.append({"type": "status", "message": "Generating 3D mesh with Tripo..."})

    import uuid
    seed_id = str(uuid.uuid4())[:8]

    try:
        tripo = TripoClient()
        glb_path, thumb_path = await tripo.generate(
            prompt=prompts["tripo_prompt"],
            output_dir=assets_dir,
            seed_id=seed_id,
        )

        icon_path = None
        try:
            seedream = SeedreamClient()
            icon_path = await seedream.generate(
                prompt=prompts["icon_prompt"],
                output_dir=assets_dir,
                seed_id=seed_id,
            )
        except Exception as e:
            logger.warning("Seedream icon failed: %s", e)

        commands.append({
            "type": "spawn_entity",
            "id": "weapon_%s" % seed_id,
            "model_path": str(glb_path) if glb_path else "",
            "position": {"x": 0, "y": 1, "z": -2},
            "rotation": {"x": 0, "y": 0, "z": 0},
            "scale": {"x": 1, "y": 1, "z": 1},
            "scripts": ["equippable"],
        })
        commands.append({
            "type": "status",
            "message": "Weapon forged: %s" % prompts["tripo_prompt"][:60],
        })

    except Exception as e:
        logger.exception("Forge pipeline failed")
        commands.append({"type": "status", "message": "Forge failed: %s" % str(e)})

    return commands


def _extract_growth_log(prompt: str) -> dict:
    """Extract combat style hints from the user prompt."""
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


def _spawn_placeholder(prompt: str) -> list[dict]:
    """Spawn a placeholder entity from a natural language request."""
    import uuid
    words = prompt.lower().split()

    entity_name = "entity"
    for skip in ["add", "spawn", "create", "place", "a", "an", "the"]:
        words = [w for w in words if w != skip]
    if words:
        entity_name = "_".join(words)

    entity_id = "%s_%s" % (entity_name, str(uuid.uuid4())[:4])

    return [{
        "type": "spawn_entity",
        "id": entity_id,
        "model_path": "",
        "position": {"x": float(hash(entity_id) % 10 - 5), "y": 0.5, "z": float(hash(entity_id + "z") % 10 - 5)},
        "scripts": [],
    }]


def _remove_entity(prompt: str) -> list[dict]:
    words = prompt.lower().split()
    for skip in ["remove", "delete", "destroy", "the", "a", "an"]:
        words = [w for w in words if w != skip]

    if not words:
        return [{"type": "status", "message": "Remove what? Specify an entity name."}]

    target = "_".join(words)
    return [{"type": "remove_entity", "id": target}]


def _attach_behavior(prompt: str) -> list[dict]:
    p = prompt.lower()

    behavior = None
    for b in ["wander", "move_to", "choppable", "equippable"]:
        if b.replace("_", " ") in p or b in p:
            behavior = b
            break

    if behavior is None:
        return [{"type": "status", "message": "Unknown behavior in: %s" % prompt}]

    return [{
        "type": "attach_behavior",
        "entity_id": "",
        "behavior": behavior,
        "params": {},
    }, {
        "type": "status",
        "message": "Specify entity_id to attach '%s' to" % behavior,
    }]
