import discord
import json
from pathlib import Path
from .buttons import BattlePromptView, PreviewPromptView


async def find(ctx, db, filter):
    """Fetch all matching rows from a data file."""
    # Get the directory where your data files are located
    # ctx parameter is kept for compatibility, but we'll use a fixed path
    data_dir = Path(__file__).parent / "data"
    path = data_dir / f"{db}.json"

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = []
    for item in data:
        success = True
        for key, value in filter.items():
            if isinstance(value, dict):
                if "$nin" in value:
                    if item[key] in value["$nin"]:
                        success = False
                        break
            else:
                if item[key] != value:
                    success = False
                    break
        if success:
            results.append(item)
    return results


async def find_one(ctx, db, filter):
    """Fetch the first matching row from a data file."""
    results = await find(ctx, db, filter)
    if results:
        return results[0]
    return None


from PIL import Image, ImageDraw, ImageFont
import os


async def generate_team_preview(battle):
    """Generates a message for trainers to preview their team with images."""
    from .buttons import PreviewPromptView

    preview_view = PreviewPromptView(battle)

    # Image configuration
    poke_width = 96
    poke_height = 96
    padding = 12
    header_height = 40

    # Calculate image dimensions
    cols = 6  # 6 Pokemon per row
    img_width = cols * poke_width + (cols + 1) * padding
    img_height = 2 * poke_height + 3 * padding + 2 * header_height

    # Create team preview image with transparent background
    team_image = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))  # Fully transparent background
    draw = ImageDraw.Draw(team_image)

    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Get the correct data directory path
    data_dir = Path(__file__).parent / "data" / "img"

    # Draw trainer 1 header with white text and semi-transparent background
    trainer1_text = f"{battle.trainer1.name}'s Team"
    text_bbox = draw.textbbox((0, 0), trainer1_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (img_width - text_width) // 2

    # Draw semi-transparent background for text readability
    draw.rectangle([text_x - 5, 5, text_x + text_width + 5, 30], fill=(0, 0, 0, 128))  # Semi-transparent black
    draw.text((text_x, 10), trainer1_text, fill=(255, 255, 255, 255), font=font)  # White text

    # Draw trainer 1 Pokemon
    y_pos = header_height
    for i, poke in enumerate(battle.trainer1.party[:6]):  # Limit to 6 Pokemon
        x_pos = padding + i * (poke_width + padding)

        # Get Pokemon ID - try different possible attributes
        poke_id = None
        if hasattr(poke, 'pokemon_id'):
            poke_id = poke.pokemon_id
        elif hasattr(poke, 'id'):
            poke_id = poke.id
        elif hasattr(poke, '_id'):
            poke_id = poke._id

        # Try to load Pokemon sprite using various possible paths
        sprite_loaded = False
        if poke_id is not None:
            # Try different possible sprite file formats and paths
            possible_paths = [
                data_dir / f"{poke_id}.png",
                data_dir / f"{poke_id}.jpg",
                data_dir / f"{poke_id}.gif",
                Path("data/img") / f"{poke_id}.png",  # Relative path fallback
                Path(f"data/img/{poke_id}.png"),  # Another fallback
            ]

            for sprite_path in possible_paths:
                if sprite_path.exists():
                    try:
                        poke_sprite = Image.open(sprite_path).convert("RGBA")
                        poke_sprite = poke_sprite.resize((poke_width, poke_height), Image.Resampling.LANCZOS)

                        # Paste sprite directly (preserving transparency)
                        team_image.paste(poke_sprite, (x_pos, y_pos), poke_sprite)
                        sprite_loaded = True
                        break
                    except Exception as e:
                        print(f"Failed to load sprite {sprite_path}: {e}")
                        continue

        if not sprite_loaded:
            # Print debug info
            print(f"Could not load sprite for Pokemon: {poke._name}, ID: {poke_id}")
            print(f"Tried paths: {[str(p) for p in possible_paths]}")

            # Draw placeholder rectangle with transparency
            placeholder = Image.new('RGBA', (poke_width, poke_height), (200, 200, 200, 128))
            team_image.paste(placeholder, (x_pos, y_pos), placeholder)
            draw.text((x_pos + 5, y_pos + poke_height // 2), "?", fill=(255, 255, 255, 255), font=font)

        # Draw Pokemon name below sprite with background for readability
        poke_name = poke._name.replace('-', ' ').title()
        name_bbox = draw.textbbox((0, 0), poke_name, font=small_font)
        name_width = name_bbox[2] - name_bbox[0]
        name_x = x_pos + (poke_width - name_width) // 2
        name_y = y_pos + poke_height + 2

        # Semi-transparent background for name
        draw.rectangle([name_x - 2, name_y - 2, name_x + name_width + 2, name_y + 14],
                       fill=(0, 0, 0, 128))
        draw.text((name_x, name_y), poke_name, fill=(255, 255, 255, 255), font=small_font)

    # Draw separator line
    separator_y = y_pos + poke_height + 25
    draw.line([(padding, separator_y), (img_width - padding, separator_y)],
              fill=(255, 255, 255, 180), width=2)  # Semi-transparent white line

    # Draw trainer 2 header
    trainer2_text = f"{battle.trainer2.name}'s Team"
    text_bbox = draw.textbbox((0, 0), trainer2_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (img_width - text_width) // 2

    # Draw semi-transparent background for text readability
    draw.rectangle([text_x - 5, separator_y + 5, text_x + text_width + 5, separator_y + 30],
                   fill=(0, 0, 0, 128))
    draw.text((text_x, separator_y + 10), trainer2_text, fill=(255, 255, 255, 255), font=font)

    # Draw trainer 2 Pokemon
    y_pos = separator_y + header_height
    for i, poke in enumerate(battle.trainer2.party[:6]):  # Limit to 6 Pokemon
        x_pos = padding + i * (poke_width + padding)

        # Get Pokemon ID - try different possible attributes
        poke_id = None
        if hasattr(poke, 'pokemon_id'):
            poke_id = poke.pokemon_id
        elif hasattr(poke, 'id'):
            poke_id = poke.id
        elif hasattr(poke, '_id'):
            poke_id = poke._id

        # Try to load Pokemon sprite using various possible paths
        sprite_loaded = False
        if poke_id is not None:
            # Try different possible sprite file formats and paths
            possible_paths = [
                data_dir / f"{poke_id}.png",
                data_dir / f"{poke_id}.jpg",
                data_dir / f"{poke_id}.gif",
                Path("data/img") / f"{poke_id}.png",  # Relative path fallback
                Path(f"data/img/{poke_id}.png"),  # Another fallback
            ]

            for sprite_path in possible_paths:
                if sprite_path.exists():
                    try:
                        poke_sprite = Image.open(sprite_path).convert("RGBA")
                        poke_sprite = poke_sprite.resize((poke_width, poke_height), Image.Resampling.LANCZOS)

                        # Paste sprite directly (preserving transparency)
                        team_image.paste(poke_sprite, (x_pos, y_pos), poke_sprite)
                        sprite_loaded = True
                        break
                    except Exception as e:
                        print(f"Failed to load sprite {sprite_path}: {e}")
                        continue

        if not sprite_loaded:
            # Print debug info
            print(f"Could not load sprite for Pokemon: {poke._name}, ID: {poke_id}")

            # Draw placeholder rectangle with transparency
            placeholder = Image.new('RGBA', (poke_width, poke_height), (200, 200, 200, 128))
            team_image.paste(placeholder, (x_pos, y_pos), placeholder)
            draw.text((x_pos + 5, y_pos + poke_height // 2), "?", fill=(255, 255, 255, 255), font=font)

        # Draw Pokemon name below sprite with background for readability
        poke_name = poke._name.replace('-', ' ').title()
        name_bbox = draw.textbbox((0, 0), poke_name, font=small_font)
        name_width = name_bbox[2] - name_bbox[0]
        name_x = x_pos + (poke_width - name_width) // 2
        name_y = y_pos + poke_height + 2

        # Semi-transparent background for name
        draw.rectangle([name_x - 2, name_y - 2, name_x + name_width + 2, name_y + 14],
                       fill=(0, 0, 0, 128))
        draw.text((name_x, name_y), poke_name, fill=(255, 255, 255, 255), font=small_font)

    # Save the image as PNG to preserve transparency
    image_path = "team_preview.png"
    team_image.save(image_path, "PNG")

    # Create embed with the team image
    embed = discord.Embed(
        title=f"Battle Team Preview",
        description=f"{battle.trainer1.name} vs {battle.trainer2.name}\nSelect your lead Pokémon!",
        color=discord.Color.blue()
    )

    # Attach the image to the embed
    file = discord.File(image_path, filename="team_preview.png")
    embed.set_image(url="attachment://team_preview.png")

    await battle.channel.send(embed=embed, file=file, view=preview_view)

    # Clean up the temporary image file
    try:
        os.remove(image_path)
    except:
        pass

    return preview_view


async def generate_main_battle_message(battle):
    """Generates a message representing the current state of the battle with sprite images and dynamic HP bars."""
    # Image configuration
    poke_width = 150
    poke_height = 150
    padding = 20
    bar_height = 25
    bar_width = 140
    name_height = 30

    img_width = poke_width * 2 + padding * 3
    img_height = poke_height + padding * 2 + bar_height + name_height + 20

    # Create image with transparent background
    battle_image = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(battle_image)

    # Font setup
    try:
        font_name = ImageFont.truetype("arial.ttf", 14)
        font_hp = ImageFont.truetype("arial.ttf", 12)
        font_small = ImageFont.truetype("arial.ttf", 10)
    except:
        font_name = ImageFont.load_default()
        font_hp = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Helper to get sprite path
    data_dir = Path(__file__).parent / "data" / "img"

    def load_sprite(poke):
        # Get Pokemon ID - try different possible attributes
        poke_id = None
        if hasattr(poke, 'pokemon_id'):
            poke_id = poke.pokemon_id
        elif hasattr(poke, 'id'):
            poke_id = poke.id
        elif hasattr(poke, '_id'):
            poke_id = poke._id

        if poke_id is None:
            return None

        # Try different possible sprite file formats and paths
        possible_paths = [
            data_dir / f"{poke_id}.png",
            data_dir / f"{poke_id}.jpg",
            data_dir / f"{poke_id}.gif",
            Path("data/img") / f"{poke_id}.png",
            Path(f"data/img/{poke_id}.png"),
        ]

        for sprite_path in possible_paths:
            if sprite_path.exists():
                try:
                    sprite = Image.open(sprite_path).convert("RGBA")
                    sprite = sprite.resize((poke_width, poke_height), Image.Resampling.LANCZOS)
                    return sprite
                except:
                    continue
        return None

    # Draw HP Bar function
    def draw_hp_bar(draw_obj, x, y, width, height, current_hp, max_hp, poke_name):
        # Background bar (dark gray)
        draw_obj.rectangle([x, y, x + width, y + height], fill=(60, 60, 60, 255))

        # Calculate fill length
        fill_width = int(width * (current_hp / max_hp)) if max_hp > 0 else 0

        # Color thresholds based on HP percentage
        ratio = current_hp / max_hp if max_hp > 0 else 0
        if ratio > 0.5:
            color = (34, 139, 34, 255)  # Forest green
        elif ratio > 0.25:
            color = (255, 165, 0, 255)  # Orange
        else:
            color = (220, 20, 60, 255)  # Crimson red

        # Filled portion of HP bar
        if fill_width > 0:
            draw_obj.rectangle([x, y, x + fill_width, y + height], fill=color)

        # Draw border around HP bar
        draw_obj.rectangle([x, y, x + width, y + height], outline=(255, 255, 255, 255), width=2)

        # HP text on the bar
        hp_text = f"{current_hp}/{max_hp}"
        hp_bbox = draw_obj.textbbox((0, 0), hp_text, font=font_hp)
        hp_text_width = hp_bbox[2] - hp_bbox[0]
        hp_text_x = x + (width - hp_text_width) // 2
        hp_text_y = y + (height - 12) // 2

        # Text shadow for better readability
        draw_obj.text((hp_text_x + 1, hp_text_y + 1), hp_text, fill=(0, 0, 0, 255), font=font_hp)
        draw_obj.text((hp_text_x, hp_text_y), hp_text, fill=(255, 255, 255, 255), font=font_hp)

    # Helper to draw Pokemon with HP bar and text
    def draw_pokemon(draw_obj, poke, x, y, is_left=True):
        # Load sprite
        sprite = load_sprite(poke)
        if sprite is None:
            # Use placeholder rectangle
            placeholder = Image.new('RGBA', (poke_width, poke_height), (200, 200, 200, 128))
            battle_image.paste(placeholder, (x, y), placeholder)
            # Draw question mark
            draw_obj.text((x + poke_width // 2 - 10, y + poke_height // 2 - 15), "?",
                          fill=(255, 255, 255, 255), font=font_name)
        else:
            battle_image.paste(sprite, (x, y), sprite)

        # Draw HP bar above sprite
        bar_x = x + (poke_width - bar_width) // 2
        bar_y = y - bar_height - 10
        max_hp = poke.starting_hp
        current_hp = max(0, poke.hp)
        draw_hp_bar(draw_obj, bar_x, bar_y, bar_width, bar_height, current_hp, max_hp, poke._name)

        # Draw Pokemon name and nickname
        name_text = poke._name.replace('-', ' ').title()
        nick_text = getattr(poke, '_nickname', None)
        if nick_text and nick_text != "None":
            display_name = f"{nick_text} ({name_text})"
        else:
            display_name = name_text

        # Calculate text position
        name_bbox = draw_obj.textbbox((0, 0), display_name, font=font_name)
        name_width = name_bbox[2] - name_bbox[0]
        name_x = x + (poke_width - name_width) // 2
        name_y = y + poke_height + 5

        # Draw semi-transparent background for name
        draw_obj.rectangle([name_x - 5, name_y - 2, name_x + name_width + 5, name_y + 18],
                           fill=(0, 0, 0, 180))
        draw_obj.text((name_x, name_y), display_name, fill=(255, 255, 255, 255), font=font_name)

        # Draw status condition if any
        if poke.nv.current:
            status_text = poke.nv.current.upper()
            status_bbox = draw_obj.textbbox((0, 0), status_text, font=font_small)
            status_width = status_bbox[2] - status_bbox[0]
            status_x = x + (poke_width - status_width) // 2
            status_y = name_y + 20

            # Status color coding
            status_colors = {
                'BURN': (255, 69, 0, 180),
                'POISON': (128, 0, 128, 180),
                'B-POISON': (148, 0, 211, 180),
                'PARALYSIS': (255, 255, 0, 180),
                'SLEEP': (70, 130, 180, 180),
                'FREEZE': (173, 216, 230, 180)
            }
            status_color = status_colors.get(status_text, (128, 128, 128, 180))

            draw_obj.rectangle([status_x - 3, status_y - 1, status_x + status_width + 3, status_y + 12],
                               fill=status_color)
            draw_obj.text((status_x, status_y), status_text, fill=(255, 255, 255, 255), font=font_small)

    # Draw left (trainer1) and right (trainer2) Pokemon
    left_x = padding
    right_x = padding * 2 + poke_width
    poke_y = padding + bar_height + 10

    draw_pokemon(draw, battle.trainer1.current_pokemon, left_x, poke_y, is_left=True)
    draw_pokemon(draw, battle.trainer2.current_pokemon, right_x, poke_y, is_left=False)

    # Save image
    image_path = "battle_msg.png"
    battle_image.save(image_path, "PNG")

    # Build description text
    desc = ""
    if battle.weather._weather_type:
        desc += f"Weather: {battle.weather._weather_type.title()}\n"
    if battle.terrain.item:
        desc += f"Terrain: {battle.terrain.item.title()}\n"
    if battle.trick_room.active():
        desc += "Trick Room: Active\n"
    desc += "\n"

    # Add detailed status for each Pokemon
    desc += f"{battle.trainer1.name}'s {battle.trainer1.current_pokemon.name}\n"
    desc += f" HP: {battle.trainer1.current_pokemon.hp}/{battle.trainer1.current_pokemon.starting_hp}\n"
    if battle.trainer1.current_pokemon.nv.current:
        desc += f" Status: {battle.trainer1.current_pokemon.nv.current}\n"
    if battle.trainer1.current_pokemon.substitute:
        desc += " Behind a substitute!\n"
    desc += "\n"
    desc += f"{battle.trainer2.name}'s {battle.trainer2.current_pokemon.name}\n"
    desc += f" HP: {battle.trainer2.current_pokemon.hp}/{battle.trainer2.current_pokemon.starting_hp}\n"
    if battle.trainer2.current_pokemon.nv.current:
        desc += f" Status: {battle.trainer2.current_pokemon.nv.current}\n"
    if battle.trainer2.current_pokemon.substitute:
        desc += " Behind a substitute!\n"

    # Create embed with the battle image
    e = discord.Embed(
        title=f"Battle between {battle.trainer1.name} and {battle.trainer2.name}",
        color=discord.Color.blue(),
        description=desc,
    )
    e.set_footer(text="Who Wins!?")
    e.set_image(url="attachment://battle_msg.png")

    try:
        battle_view = BattlePromptView(battle)
        file = discord.File(image_path, filename="battle_msg.png")
        await battle.channel.send(embed=e, file=file, view=battle_view)
    except RuntimeError:
        pass

    # Clean up the temporary image file
    try:
        os.remove(image_path)
    except:
        pass

    return battle_view


async def generate_text_battle_message(battle):
    """
    Send battle.msg in a boilerplate embed.
    Handles the message being too long.
    """
    page = ""
    pages = []
    base_embed = discord.Embed(color=discord.Color.blue())  # Fixed color
    raw = battle.msg.strip().split("\n")

    for part in raw:
        if len(page + part) > 2000:
            embed = base_embed.copy()
            embed.description = page.strip()
            pages.append(embed)
            page = ""
        page += part + "\n"

    page = page.strip()
    if page:
        embed = base_embed.copy()
        embed.description = page
        pages.append(embed)

    for page in pages:
        await battle.channel.send(embed=page)

    battle.msg = ""
