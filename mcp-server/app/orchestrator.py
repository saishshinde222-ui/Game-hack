import logging
import random
import uuid
from pathlib import Path

from app.clients.seedream import SeedreamClient
from app.clients.seedance import SeedanceClient
from app.utils.sprites import convert_video_to_spritesheet, remove_background_and_trim

logger = logging.getLogger(__name__)

SPAWN_WORDS = ["add", "spawn", "create", "place", "make", "generate", "build", "forge", "craft"]
REMOVE_WORDS = ["remove", "delete", "destroy"]
BEHAVIOR_WORDS = ["wander", "move to", "move_to"]
ANIMATE_WORDS = ["animate", "walk", "run", "idle", "attack", "dance", "jump"]

DEFAULT_GROUND_Y = 597.0
VIEWPORT_WIDTH = 1280
SPAWN_X_MIN = 100
SPAWN_X_MAX = 1180

DESIRED_HEIGHT_CHARACTER = 200
DESIRED_HEIGHT_OBJECT = 180
DESIRED_HEIGHT_ITEM = 80

ANIMATED_ENTITY_WORDS = [
    "character", "hero", "player", "warrior", "creature", "monster",
    "npc", "person", "knight", "wizard", "mage", "goblin", "skeleton",
    "slime", "dragon", "cat", "dog", "bird", "fish", "villager",
]

STATIC_OBJECT_WORDS = [
    "tree", "rock", "house", "castle", "chair", "table", "chest",
    "barrel", "lamp", "statue", "pillar", "fountain", "bridge",
    "tower", "gate", "wall", "fence", "bench", "torch", "throne",
    "flower", "bush", "crate", "sign", "door", "window", "path",
]

ITEM_WORDS = [
    "sword", "blade", "axe", "hammer", "dagger", "spear", "staff", "bow",
    "shield", "mace", "weapon", "knife", "katana", "scythe", "wand",
    "potion", "gem", "coin", "key", "ring", "amulet", "scroll", "book",
]


async def handle_user_prompt(prompt: str, context: dict, assets_dir: Path) -> list[dict]:
    p = prompt.lower().strip()

    if _matches(p, REMOVE_WORDS):
        return _remove_entity(prompt)

    if _is_animate_existing(p, context):
        return await _animate_existing_entity(prompt, p, context, assets_dir)

    if _matches(p, BEHAVIOR_WORDS):
        return _attach_behavior(prompt)

    if _should_spawn(p):
        if _matches(p, ANIMATED_ENTITY_WORDS):
            return await _spawn_animated_entity(prompt, assets_dir)
        return await _spawn_static_entity(prompt, assets_dir)

    return [{"type": "status", "message": "Command not recognized: %s" % prompt}]


def _matches(p: str, words: list[str]) -> bool:
    return any(w in p for w in words)


def _should_spawn(p: str) -> bool:
    return _matches(p, SPAWN_WORDS)


def _is_animate_existing(p: str, context: dict) -> bool:
    """Check if the user wants to animate an already-spawned entity."""
    if not _matches(p, ANIMATE_WORDS):
        return False
    if not _matches(p, SPAWN_WORDS):
        return True
    return False


def _extract_entity_name(prompt: str) -> str:
    words = prompt.lower().split()
    skip = set(SPAWN_WORDS + REMOVE_WORDS + ["a", "an", "the", "me", "for", "with", "that"])
    words = [w for w in words if w not in skip]
    return "_".join(words[:3]) if words else "entity"


def _extract_target_entity(prompt: str, context: dict) -> str | None:
    """Try to find an entity ID referenced in the prompt from the current entity list."""
    entities = context.get("entities", [])
    p = prompt.lower()
    for ent in entities:
        eid = ent if isinstance(ent, str) else ent.get("id", "")
        if eid and eid.lower() in p:
            return eid
    return None


# ---------------------------------------------------------------------------
# Static sprite spawn (Seedream only)
# ---------------------------------------------------------------------------

async def _spawn_static_entity(prompt: str, assets_dir: Path) -> list[dict]:
    seed_id = str(uuid.uuid4())[:8]
    entity_id = _extract_entity_name(prompt) + "_%s" % seed_id
    is_item = _matches(prompt.lower(), ITEM_WORDS)
    sprite_prompt = _build_sprite_prompt(prompt, is_item=is_item)

    commands: list[dict] = []
    commands.append({"type": "status", "message": "Generating sprite: %s" % sprite_prompt[:80]})

    try:
        seedream = SeedreamClient()
        result = await seedream.generate(sprite_prompt, assets_dir, seed_id)

        await remove_background_and_trim(result.path)

        desired_h = DESIRED_HEIGHT_ITEM if is_item else DESIRED_HEIGHT_OBJECT
        spawn_x = random.randint(SPAWN_X_MIN, SPAWN_X_MAX)

        commands.append({
            "type": "spawn_entity",
            "id": entity_id,
            "texture_path": str(result.path),
            "position": {"x": spawn_x, "y": 0},
            "desired_height": desired_h,
        })
        commands.append({"type": "status", "message": "Spawned: %s" % entity_id})

    except Exception as e:
        logger.exception("Static sprite generation failed")
        commands.append({"type": "status", "message": "Generation failed: %s" % str(e)})

    return commands


# ---------------------------------------------------------------------------
# Animated sprite spawn (Seedream → Seedance → spritesheet)
# ---------------------------------------------------------------------------

async def _spawn_animated_entity(prompt: str, assets_dir: Path) -> list[dict]:
    seed_id = str(uuid.uuid4())[:8]
    entity_id = _extract_entity_name(prompt) + "_%s" % seed_id

    commands: list[dict] = []
    commands.append({"type": "status", "message": "Generating animated sprite..."})

    spawn_x = random.randint(SPAWN_X_MIN, SPAWN_X_MAX)

    try:
        seedream = SeedreamClient()
        ref_prompt = _build_character_prompt(prompt)
        ref_result = await seedream.generate(ref_prompt, assets_dir, seed_id)

        await remove_background_and_trim(ref_result.path)

        commands.append({"type": "status", "message": "Reference sprite ready, generating animation..."})

        seedance = SeedanceClient()
        anim_prompt = _build_animation_prompt(prompt)
        video_path = await seedance.image_to_video(
            image_url=ref_result.url,
            prompt=anim_prompt,
            output_dir=assets_dir,
            seed_id=seed_id,
        )

        if video_path and video_path.exists():
            meta = await convert_video_to_spritesheet(
                video_path=video_path,
                output_dir=assets_dir,
                seed_id=seed_id,
            )
            if meta:
                commands.append({
                    "type": "spawn_animated_entity",
                    "id": entity_id,
                    "spritesheet_path": str(meta.path),
                    "frame_count": meta.frame_count,
                    "columns": meta.columns,
                    "fps": 8,
                    "position": {"x": spawn_x, "y": 0},
                    "desired_height": DESIRED_HEIGHT_CHARACTER,
                })
                commands.append({"type": "status", "message": "Spawned animated: %s" % entity_id})
                return commands

        commands.append({"type": "status", "message": "Animation failed, spawning static sprite"})
        commands.append({
            "type": "spawn_entity",
            "id": entity_id,
            "texture_path": str(ref_result.path),
            "position": {"x": spawn_x, "y": 0},
            "desired_height": DESIRED_HEIGHT_CHARACTER,
        })
        commands.append({"type": "status", "message": "Spawned (static fallback): %s" % entity_id})

    except Exception as e:
        logger.exception("Animated sprite generation failed")
        commands.append({"type": "status", "message": "Generation failed: %s" % str(e)})

    return commands


# ---------------------------------------------------------------------------
# Animate an existing entity (Seedance → spritesheet → update_animation)
# ---------------------------------------------------------------------------

async def _animate_existing_entity(
    prompt: str, p: str, context: dict, assets_dir: Path
) -> list[dict]:
    seed_id = str(uuid.uuid4())[:8]
    entity_id = _extract_target_entity(prompt, context)

    if not entity_id:
        return [{"type": "status", "message": "Which entity? Specify a name. Known: %s" %
                 ", ".join(_get_entity_ids(context))}]

    commands: list[dict] = []

    animation_name = "idle"
    for anim in ["walk", "run", "attack", "dance", "jump", "idle"]:
        if anim in p:
            animation_name = anim
            break

    commands.append({"type": "status", "message": "Generating %s animation for %s..." % (animation_name, entity_id)})

    try:
        seedance = SeedanceClient()
        anim_prompt = "2D game character %s animation cycle, side view, smooth motion, clean background" % animation_name

        video_path = await seedance.text_to_video(
            prompt=anim_prompt,
            output_dir=assets_dir,
            seed_id=seed_id,
            ratio="1:1",
        )

        if video_path and video_path.exists():
            meta = await convert_video_to_spritesheet(
                video_path=video_path,
                output_dir=assets_dir,
                seed_id=seed_id,
            )
            if meta:
                commands.append({
                    "type": "update_animation",
                    "entity_id": entity_id,
                    "animation_name": animation_name,
                    "spritesheet_path": str(meta.path),
                    "frame_count": meta.frame_count,
                    "columns": meta.columns,
                    "fps": 8,
                })
                commands.append({"type": "status", "message": "Animation '%s' applied to %s" % (animation_name, entity_id)})
                return commands

        commands.append({"type": "status", "message": "Animation generation failed for %s" % entity_id})

    except Exception as e:
        logger.exception("Animation generation failed")
        commands.append({"type": "status", "message": "Animation failed: %s" % str(e)})

    return commands


# ---------------------------------------------------------------------------
# Behavior / remove (unchanged logic, 2D positions)
# ---------------------------------------------------------------------------

def _remove_entity(prompt: str) -> list[dict]:
    words = prompt.lower().split()
    skip = set(REMOVE_WORDS + ["the", "a", "an"])
    words = [w for w in words if w not in skip]
    if not words:
        return [{"type": "status", "message": "Remove what?"}]
    return [{"type": "remove_entity", "id": "_".join(words)}]


def _attach_behavior(prompt: str) -> list[dict]:
    p = prompt.lower()
    behavior = None
    for b in ["wander", "move_to"]:
        if b.replace("_", " ") in p or b in p:
            behavior = b
            break
    if behavior is None:
        return [{"type": "status", "message": "Unknown behavior: %s" % prompt}]

    entity_hint = _extract_entity_name(prompt)
    return [{
        "type": "attach_behavior",
        "entity_id": entity_hint,
        "behavior": behavior,
        "params": {},
    }, {"type": "status", "message": "Attached '%s' to '%s'" % (behavior, entity_hint)}]


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_sprite_prompt(prompt: str, is_item: bool = False) -> str:
    clean = prompt.strip()
    for skip in SPAWN_WORDS + ["a", "an", "the"]:
        clean = clean.replace(skip, "", 1).strip()

    if is_item:
        return "2D game item icon, %s, centered, clean transparent background, detailed, stylized" % clean
    return "2D game sprite, %s, side view, clean transparent background, detailed, stylized" % clean


def _build_character_prompt(prompt: str) -> str:
    clean = prompt.strip()
    for skip in SPAWN_WORDS + ["a", "an", "the"]:
        clean = clean.replace(skip, "", 1).strip()
    return (
        "2D game character sprite, %s, side view, full body, "
        "clean transparent background, colorful, stylized" % clean
    )


def _build_animation_prompt(prompt: str) -> str:
    clean = prompt.strip()
    for skip in SPAWN_WORDS + ["a", "an", "the"]:
        clean = clean.replace(skip, "", 1).strip()
    return "2D game character idle breathing animation, %s, side view, smooth motion, clean background" % clean


def _get_entity_ids(context: dict) -> list[str]:
    entities = context.get("entities", [])
    return [
        (ent if isinstance(ent, str) else ent.get("id", ""))
        for ent in entities
    ]
