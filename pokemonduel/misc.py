import random
from .enums import Ability, ElementType


class ExpiringEffect():
    """
    Some effect that has a specific amount of time it is active.

    turns_to_expire can be None, in which case this effect never expires.
    """

    def __init__(self, turns_to_expire: int):
        self._remaining_turns = turns_to_expire

    def active(self):
        """Returns True if this effect is still active, False otherwise."""
        if self._remaining_turns is None:
            return True
        return bool(self._remaining_turns)

    def next_turn(self):
        """
        Progresses this effect for a turn.

        Returns True if the effect just ended.
        """
        if self._remaining_turns is None:
            return False
        if self.active():
            self._remaining_turns -= 1
            return not self.active()
        return False

    def set_turns(self, turns_to_expire):
        """Set the amount of turns until this effect expires."""
        self._remaining_turns = turns_to_expire


class Weather(ExpiringEffect):
    """
    The current weather of the battlefield.

    Options:
    -hail
    -sandstorm
    -h-rain
    -rain
    -h-sun
    -sun
    -h-wind
    """

    def __init__(self, battle):
        super().__init__(0)
        self._weather_type = ""
        self.battle = battle

    def _expire_weather(self):
        """Clear the current weather and update Castform forms."""
        self._weather_type = ""
        for poke in (self.battle.trainer1.current_pokemon, self.battle.trainer2.current_pokemon):
            if poke is None:
                continue
            # Forecast
            if poke.ability() == Ability.FORECAST and poke._name in ("Castform-snowy", "Castform-rainy",
                                                                     "Castform-sunny"):
                if poke.form("Castform"):
                    poke.type_ids = [ElementType.NORMAL]

    def next_turn(self):
        """Progresses the weather a turn."""
        if super().next_turn():
            self._expire_weather()
            return True
        return False

    def recheck_ability_weather(self):
        """Checks if strong weather effects from a pokemon with a weather ability need to be removed."""
        maintain_weather = False
        for poke in (self.battle.trainer1.current_pokemon, self.battle.trainer2.current_pokemon):
            if poke is None:
                continue
            if self._weather_type == "h-wind" and poke.ability() == Ability.DELTA_STREAM:
                maintain_weather = True
            if self._weather_type == "h-sun" and poke.ability() == Ability.DESOLATE_LAND:
                maintain_weather = True
            if self._weather_type == "h-rain" and poke.ability() == Ability.PRIMORDIAL_SEA:
                maintain_weather = True

        if self._weather_type in ("h-wind", "h-sun", "h-rain") and not maintain_weather:
            self._expire_weather()
            return True
        return False

    def get(self):
        """Get the current weather type."""
        for poke in (self.battle.trainer1.current_pokemon, self.battle.trainer2.current_pokemon):
            if poke is None:
                continue
            if poke.ability() in (Ability.CLOUD_NINE, Ability.AIR_LOCK):
                return ""
        return self._weather_type

    def set(self, weather: str, pokemon):
        """
        Set the weather, lasting a certain number of turns.

        Returns a formatted message indicating any weather change.
        """
        msg = ""
        turns = None
        element = None
        castform = None
        if self._weather_type == weather:
            return ""
        if weather == "hail":
            if self._weather_type in ("h-rain", "h-sun", "h-wind"):
                return ""
            if pokemon.held_item == "icy-rock":
                turns = 8
            else:
                turns = 5
            msg += "It starts to hail!\n"
            element = ElementType.ICE
            castform = "Castform-snowy"
        elif weather == "sandstorm":
            if self._weather_type in ("h-rain", "h-sun", "h-wind"):
                return ""
            if pokemon.held_item == "smooth-rock":
                turns = 8
            else:
                turns = 5
            msg += "A sandstorm is brewing up!\n"
            element = ElementType.NORMAL
            castform = "Castform"
        elif weather == "rain":
            if self._weather_type in ("h-rain", "h-sun", "h-wind"):
                return ""
            if pokemon.held_item == "damp-rock":
                turns = 8
            else:
                turns = 5
            msg += "It starts to rain!\n"
            element = ElementType.WATER
            castform = "Castform-rainy"
        elif weather == "sun":
            if self._weather_type in ("h-rain", "h-sun", "h-wind"):
                return ""
            if pokemon.held_item == "heat-rock":
                turns = 8
            else:
                turns = 5
            msg += "The sunlight is strong!\n"
            element = ElementType.FIRE
            castform = "Castform-sunny"
        elif weather == "h-rain":
            msg += "Heavy rain begins to fall!\n"
            element = ElementType.WATER
            castform = "Castform-rainy"
        elif weather == "h-sun":
            msg += "The sunlight is extremely harsh!\n"
            element = ElementType.FIRE
            castform = "Castform-sunny"
        elif weather == "h-wind":
            msg += "The winds are extremely strong!\n"
            element = ElementType.NORMAL
            castform = "Castform"
        else:
            raise ValueError("unexpected weather")

        # Forecast
        t = ElementType(element).name.lower()
        for poke in (self.battle.trainer1.current_pokemon, self.battle.trainer2.current_pokemon):
            if poke is None:
                continue
            if poke.ability() == Ability.FORECAST and poke._name != castform:
                if poke.form(castform):
                    poke.type_ids = [element]
                    msg += f"{poke.name} transformed into a {t} type using its forecast!\n"

        self._weather_type = weather
        self._remaining_turns = turns
        return msg


class LockedMove(ExpiringEffect):
    """A multi-turn move that a pokemon is locked into."""

    def __init__(self, move, turns_to_expire: int):
        super().__init__(turns_to_expire)
        self.move = move
        self.turn = 0

    def next_turn(self):
        """Progresses the move a turn."""
        expired = super().next_turn()
        self.turn += 1
        return expired

    def is_last_turn(self):
        """Returns True if this is the last turn this move will be used."""
        return self._remaining_turns == 1


class ExpiringItem(ExpiringEffect):
    """An expiration timer with some data."""

    def __init__(self):
        super().__init__(0)
        self.item = None

    def next_turn(self):
        """Progresses the effect a turn."""
        expired = super().next_turn()
        if expired:
            self.item = None
        return expired

    def set(self, item, turns: int):
        """Set the item and turns until expiration."""
        self.item = item
        self._remaining_turns = turns

    def end(self):
        """Ends this expiring item."""
        self.item = None
        self._remaining_turns = 0


class Terrain(ExpiringItem):
    """The terrain of the battle"""

    def __init__(self, battle):
        super().__init__()
        self.battle = battle

    def next_turn(self):
        """Progresses the effect a turn."""
        expired = super().next_turn()
        if expired:
            self.end()
        return expired

    def set(self, item, attacker):
        """
        Set the terrain and turns until expiration.

        Returns a formatted string.
        """
        if item == self.item:
            return f"There's already a {item} terrain!\n"
        turns = 8 if attacker.held_item == "terrain-extender" else 5
        super().set(item, turns)
        msg = f"{attacker.name} creates a{'n' if item == 'electric' else ''} {item} terrain!\n"
        # Mimicry
        element = None
        if item == "electric":
            element = ElementType.ELECTRIC
        elif item == "grassy":
            element = ElementType.GRASS
        elif item == "misty":
            element = ElementType.FAIRY
        elif item == "psychic":
            element = ElementType.PSYCHIC
        for poke in (self.battle.trainer1.current_pokemon, self.battle.trainer2.current_pokemon):
            if poke is None:
                continue
            if poke.ability() == Ability.MIMICRY:
                poke.type_ids = [element]
                t = ElementType(element).name.lower()
                msg += f"{poke.name} became a {t} type using its mimicry!\n"
            if poke.held_item == "electric-seed" and item == "electric":
                msg += poke.append_defense(1, attacker=poke, source="its electric seed")
                poke.held_item.use()
            if poke.held_item == "psychic-seed" and item == "psychic":
                msg += poke.append_spdef(1, attacker=poke, source="its psychic seed")
                poke.held_item.use()
            if poke.held_item == "misty-seed" and item == "misty":
                msg += poke.append_spdef(1, attacker=poke, source="its misty seed")
                poke.held_item.use()
            if poke.held_item == "grassy-seed" and item == "grassy":
                msg += poke.append_defense(1, attacker=poke, source="its grassy seed")
                poke.held_item.use()
        return msg

    def end(self):
        """Ends the terrain."""
        super().end()
        # Mimicry
        for poke in (self.battle.trainer1.current_pokemon, self.battle.trainer2.current_pokemon):
            if poke is None:
                continue
            if poke.ability() == Ability.MIMICRY:
                poke.type_ids = poke.starting_type_ids.copy()


class ExpiringWish(ExpiringEffect):
    """Stores the HP and when to heal for the move Wish."""

    def __init__(self):
        super().__init__(0)
        self.hp = None

    def next_turn(self):
        """Progresses the effect a turn."""
        expired = super().next_turn()
        hp = 0
        if expired:
            hp = self.hp
            self.hp = None
        return hp

    def set(self, hp):
        """Set the move and turns until expiration."""
        self.hp = hp
        self._remaining_turns = 2


class NonVolatileEffect():
    """The current non volatile effect status."""

    def __init__(self, pokemon):
        self.current = ""
        self.pokemon = pokemon
        self.sleep_timer = ExpiringEffect(0)
        self.badly_poisoned_turn = 0

    def next_turn(self, battle):
        """
        Progresses this status by a turn.

        Returns a formatted string if a status wore off.
        """
        if not self.current:
            return ""
        if self.current == "b-poison":
            self.badly_poisoned_turn += 1
        if self.pokemon.ability() == Ability.HYDRATION and battle.weather.get() in ("rain", "h-rain"):
            removed = self.current
            self.reset()
            return f"{self.pokemon.name}'s hydration cured its {removed}!\n"
        if self.pokemon.ability() == Ability.SHED_SKIN and not random.randint(0, 2):
            removed = self.current
            self.reset()
            return f"{self.pokemon.name}'s shed skin cured its {removed}!\n"
        # The poke still has a status effect, apply damage
        if self.current == "burn":
            damage = max(1, self.pokemon.starting_hp // 16)
            if self.pokemon.ability() == Ability.HEATPROOF:
                damage //= 2
            return self.pokemon.damage(damage, battle, source="its burn")
        if self.current == "b-poison":
            if self.pokemon.ability() == Ability.POISON_HEAL:
                return self.pokemon.heal(self.pokemon.starting_hp // 8, source="its poison heal")
            damage = max(1, (self.pokemon.starting_hp // 16) * min(15, self.badly_poisoned_turn))
            return self.pokemon.damage(damage, battle, source="its bad poison")
        if self.current == "poison":
            if self.pokemon.ability() == Ability.POISON_HEAL:
                return self.pokemon.heal(self.pokemon.starting_hp // 8, source="its poison heal")
            damage = max(1, self.pokemon.starting_hp // 8)
            return self.pokemon.damage(damage, battle, source="its poison")
        if self.current == "sleep" and self.pokemon.nightmare:
            return self.pokemon.damage(self.pokemon.starting_hp // 4, battle, source="its nightmare")
        return ""

    def burn(self):
        """Returns True if the pokemon is burned."""
        return self.current == "burn"

    def sleep(self):
        """Returns True if the pokemon is asleep."""
        if self.pokemon.ability() == Ability.COMATOSE:
            return True
        return self.current == "sleep"

    def poison(self):
        """Returns True if the pokemon is poisoned."""
        return self.current in ("poison", "b-poison")

    def paralysis(self):
        """Returns True if the pokemon is paralyzed."""
        return self.current == "paralysis"

    def freeze(self):
        """Returns True if the pokemon is frozen."""
        return self.current == "freeze"

    def apply_status(self, status, battle, *, attacker=None, move=None, turns=None, force=False, source: str = ""):
        """
        Apply a non volatile status to a pokemon.

        Returns a formatted message.
        """
        msg = ""
        if source:
            source = f" from {source}"
        if self.current and not force:
            return f"{self.pokemon.name} already has a status, it can't get {status} too!\n"
        if self.pokemon.ability(attacker=attacker, move=move) == Ability.COMATOSE:
            return f"{self.pokemon.name} already has a status, it can't get {status} too!\n"
        if self.pokemon.ability(attacker=attacker, move=move) == Ability.PURIFYING_SALT:
            return f"{self.pokemon.name}'s purifying salt protects it from being inflicted with {status}!\n"
        if self.pokemon.ability(attacker=attacker, move=move) == Ability.LEAF_GUARD and battle.weather.get() in ("sun",
                                                                                                                 "h-sun"):
            return f"{self.pokemon.name}'s leaf guard protects it from being inflicted with {status}!\n"
        if self.pokemon.substitute and attacker is not self.pokemon and (
                move is None or move.is_affected_by_substitute()):
            return f"{self.pokemon.name}'s substitute protects it from being inflicted with {status}!\n"
        if self.pokemon.owner.safeguard.active() and attacker is not self.pokemon and (
                attacker is None or attacker.ability() != Ability.INFILTRATOR):
            return f"{self.pokemon.name}'s safeguard protects it from being inflicted with {status}!\n"
        if self.pokemon.grounded(battle, attacker=attacker, move=move) and battle.terrain.item == "misty":
            return f"The misty terrain protects {self.pokemon.name} from being inflicted with {status}!\n"
        if self.pokemon.ability(attacker=attacker,
                                move=move) == Ability.FLOWER_VEIL and ElementType.GRASS in self.pokemon.type_ids:
            return f"{self.pokemon.name}'s flower veil protects it from being inflicted with {status}!\n"
        if self.pokemon._name == "Minior":
            return "Minior's hard shell protects it from status effects!\n"
        if status == "burn":
            if ElementType.FIRE in self.pokemon.type_ids:
                return f"{self.pokemon.name} is a fire type and can't be burned!\n"
            if self.pokemon.ability(attacker=attacker, move=move) in (Ability.WATER_VEIL, Ability.WATER_BUBBLE):
                ability_name = Ability(self.pokemon.ability_id).pretty_name
                return f"{self.pokemon.name}'s {ability_name} prevents it from getting burned!\n"
            self.current = status
            msg += f"{self.pokemon.name} was burned{source}!\n"
        if status == "sleep":
            if self.pokemon.ability(attacker=attacker, move=move) in (Ability.INSOMNIA, Ability.VITAL_SPIRIT,
                                                                      Ability.SWEET_VEIL):
                ability_name = Ability(self.pokemon.ability_id).pretty_name
                return f"{self.pokemon.name}'s {ability_name} keeps it awake!\n"
            if self.pokemon.grounded(battle, attacker=attacker, move=move) and battle.terrain.item == "electric":
                return f"The terrain is too electric for {self.pokemon.name} to fall asleep!\n"
            if battle.trainer1.current_pokemon and battle.trainer1.current_pokemon.uproar.active():
                return f"An uproar keeps {self.pokemon.name} from falling asleep!\n"
            if battle.trainer2.current_pokemon and battle.trainer2.current_pokemon.uproar.active():
                return f"An uproar keeps {self.pokemon.name} from falling asleep!\n"
            if turns is None:
                turns = random.randint(2, 4)
            if self.pokemon.ability(attacker=attacker, move=move) == Ability.EARLY_BIRD:
                turns //= 2
            self.current = status
            self.sleep_timer.set_turns(turns)
            msg += f"{self.pokemon.name} fell asleep{source}!\n"
        if status in ("poison", "b-poison"):
            if attacker is None or attacker.ability() != Ability.CORROSION:
                if ElementType.STEEL in self.pokemon.type_ids:
                    return f"{self.pokemon.name} is a steel type and can't be poisoned!\n"
                if ElementType.POISON in self.pokemon.type_ids:
                    return f"{self.pokemon.name} is a poison type and can't be poisoned!\n"
            if self.pokemon.ability(attacker=attacker, move=move) in (Ability.IMMUNITY, Ability.PASTEL_VEIL):
                ability_name = Ability(self.pokemon.ability_id).pretty_name
                return f"{self.pokemon.name}'s {ability_name} keeps it from being poisoned!\n"
            self.current = status
            bad = " badly" if status == "b-poison" else ""
            msg += f"{self.pokemon.name} was{bad} poisoned{source}!\n"

            if move is not None and attacker is not None and attacker.ability() == Ability.POISON_PUPPETEER:
                msg += self.pokemon.confuse(attacker=attacker, source=f"{attacker.name}'s poison puppeteer")
        if status == "paralysis":
            if ElementType.ELECTRIC in self.pokemon.type_ids:
                return f"{self.pokemon.name} is an electric type and can't be paralyzed!\n"
            if self.pokemon.ability(attacker=attacker, move=move) == Ability.LIMBER:
                return f"{self.pokemon.name}'s limber keeps it from being paralyzed!\n"
            self.current = status
            msg += f"{self.pokemon.name} was paralyzed{source}!\n"
        if status == "freeze":
            if ElementType.ICE in self.pokemon.type_ids:
                return f"{self.pokemon.name} is an ice type and can't be frozen!\n"
            if self.pokemon.ability(attacker=attacker, move=move) == Ability.MAGMA_ARMOR:
                return f"{self.pokemon.name}'s magma armor keeps it from being frozen!\n"
            if battle.weather.get() in ("sun", "h-sun"):
                return f"It's too sunny to freeze {self.pokemon.name}!\n"
            self.current = status
            msg += f"{self.pokemon.name} was frozen solid{source}!\n"

        if self.pokemon.ability(attacker=attacker, move=move) == Ability.SYNCHRONIZE and attacker is not None:
            msg += attacker.nv.apply_status(status, battle, attacker=self.pokemon,
                                            source=f"{self.pokemon.name}'s synchronize")

        if self.pokemon.held_item.should_eat_berry_status(attacker):
            msg += self.pokemon.held_item.eat_berry(attacker=attacker, move=move)

        return msg

    def reset(self):
        """Remove a non volatile status from a pokemon."""
        self.current = ""
        self.badly_poisoned_turn = 0
        self.sleep_timer.set_turns(0)
        self.pokemon.nightmare = False


class Metronome():
    """Holds recent move status for the held item metronome."""

    def __init__(self):
        self.move = ""
        self.count = 0

    def reset(self):
        """A move failed or a non-move action was done."""
        self.move = ""
        self.count = 0

    def use(self, movename):
        """Updates the metronome based on a used move."""
        if self.move == movename:
            self.count += 1
        else:
            self.move = movename
            self.count = 1

    def get_buff(self, movename):
        """Get the buff multiplier for this metronome."""
        if self.move != movename:
            return 1
        return min(2, 1 + (.2 * self.count))


class Item():
    """Stores information about an item."""

    def __init__(self, item_data):
        self.name = item_data["identifier"]
        self.id = item_data["id"]
        self.power = item_data["fling_power"]
        self.effect = item_data["fling_effect_id"]


class HeldItem():
    """Stores information about the current held item for a particular poke."""

    def __init__(self, item_data, owner):
        if item_data is None:
            self.item = None
        else:
            self.item = Item(item_data)
        self.owner = owner
        self.battle = None
        self.last_used = None
        self.ever_had_item = self.item is not None

    def get(self):
        """Get the current held item identifier."""
        if self.item is None:
            return None
        if not self.can_remove():
            return self.item.name
        if self.owner.embargo.active():
            return None
        if self.battle and self.battle.magic_room.active():
            return None
        if self.owner.ability() == Ability.KLUTZ:
            return None
        if self.owner.corrosive_gas:
            return None
        return self.item.name

    def has_item(self):
        """Helper method to prevent attempting to acquire a new item if the poke already has one."""
        return self.item is not None

    def can_remove(self):
        """Returns a boolean indicating whether this held item can be removed."""
        return self.name not in (
            # Plates
            "draco-plate", "dread-plate", "earth-plate", "fist-plate", "flame-plate", "icicle-plate",
            "insect-plate", "iron-plate", "meadow-plate", "mind-plate", "pixie-plate", "sky-plate",
            "splash-plate", "spooky-plate", "stone-plate", "toxic-plate", "zap-plate",
            # Memories
            "dragon-memory", "dark-memory", "ground-memory", "fighting-memory", "fire-memory",
            "ice-memory", "bug-memory", "steel-memory", "grass-memory", "psychic-memory",
            "fairy-memory", "flying-memory", "water-memory", "ghost-memory", "rock-memory",
            "poison-memory", "electric-memory",
            # Misc
            "primal-orb", "griseous-orb", "blue-orb", "red-orb", "rusty-sword", "rusty-shield",
            # Mega Stones
            "mega-stone", "mega-stone-x", "mega-stone-y",
        )

    def is_berry(self, *, only_active=True):
        """
        Returns a boolean indicating whether this held item is a berry.

        The optional param only_active determines if this method should only return True if the berry is active and usable.
        """
        if only_active:
            return self.get() is not None and self.get().endswith("-berry")
        return self.name is not None and self.name.endswith("-berry")

    def remove(self):
        """Remove this held item, setting it to None."""
        if not self.can_remove():
            raise ValueError(f"{self.name} cannot be removed.")
        self.item = None

    def use(self):
        """Uses this item, setting it to None but also recording that it was used."""
        if not self.can_remove():
            raise ValueError(f"{self.name} cannot be removed.")
        self.last_used = self.item
        self.owner.choice_move = None
        self.remove()

    def transfer(self, other):
        """Transfer the data of this held item to other, and clear this item."""
        if not self.can_remove():
            raise ValueError(f"{self.name} cannot be removed.")
        if not other.can_remove():
            raise ValueError(f"{other.name} cannot be removed.")
        other.item = self.item
        self.remove()

    def swap(self, other):
        """Swap the date between this held item and other."""
        if not self.can_remove():
            raise ValueError(f"{self.name} cannot be removed.")
        if not other.can_remove():
            raise ValueError(f"{other.name} cannot be removed.")
        self.item, other.item = other.item, self.item
        self.owner.choice_move = None
        other.owner.choice_move = None
        self.ever_had_item = self.ever_had_item or self.item is not None

    def recover(self, other):
        """Recover & claim the last_used item from other."""
        self.item = other.last_used
        other.last_used = None
        self.ever_had_item = self.ever_had_item or self.item is not None

    def _should_eat_berry_util(self, otherpoke=None):
        """Util for all the things that are shared between the different kinds of berry."""
        if self.owner.hp == 0:
            return False
        if otherpoke is not None and otherpoke.ability() in (Ability.UNNERVE, Ability.AS_ONE_SHADOW,
                                                             Ability.AS_ONE_ICE):
            return False
        if not self.is_berry():
            return False
        return True

    def should_eat_berry_damage(self, otherpoke=None):
        """Returns True if the pokemon meets the criteria to eat its held berry after being damaged."""
        if not self._should_eat_berry_util(otherpoke):
            return False
        if self.owner.hp <= self.owner.starting_hp / 4:
            if self in (
                    # HP berries
                    "figy-berry", "wiki-berry", "mago-berry", "aguav-berry", "iapapa-berry",
                    # Stat berries
                    "apicot-berry", "ganlon-berry", "lansat-berry", "liechi-berry", "micle-berry", "petaya-berry",
                    "salac-berry", "starf-berry",
                    # Additional berries
                    "oran-berry", "leppa-berry", "custap-berry", "jaboca-berry", "rowap-berry",
            ):
                return True
        if self.owner.hp <= self.owner.starting_hp / 2:
            if self.owner.ability() == Ability.GLUTTONY:
                return True
            if self == "sitrus-berry":
                return True
        return False

    def should_eat_berry_status(self, otherpoke=None):
        """Returns True if the pokemon meets the criteria to eat its held berry after getting a status."""
        if not self._should_eat_berry_util(otherpoke):
            return False
        if self in ("aspear-berry", "lum-berry") and self.owner.nv.freeze():
            return True
        if self in ("cheri-berry", "lum-berry") and self.owner.nv.paralysis():
            return True
        if self in ("chesto-berry", "lum-berry") and self.owner.nv.sleep():
            return True
        if self in ("pecha-berry", "lum-berry") and self.owner.nv.poison():
            return True
        if self in ("rawst-berry", "lum-berry") and self.owner.nv.burn():
            return True
        if self in ("persim-berry", "lum-berry") and self.owner.confusion.active():
            return True
        return False

    def should_eat_berry(self, otherpoke=None):
        """Returns True if the pokemon meets the criteria to eat its held berry."""
        return self.should_eat_berry_damage(otherpoke) or self.should_eat_berry_status(otherpoke)

    def get_damage_multiplier(self, move_type, attacker=None, move=None, is_super_effective=False,
                              is_not_very_effective=False):
        """Get damage multiplier for held items that affect damage calculation."""
        multiplier = 1.0

        # Type-boosting items (1.2x damage)
        type_items = {
            ElementType.NORMAL: ["silk-scarf", "normalium-z"],
            ElementType.FIRE: ["charcoal", "firium-z"],
            ElementType.WATER: ["mystic-water", "waterium-z"],
            ElementType.ELECTRIC: ["magnet", "electrium-z"],
            ElementType.GRASS: ["miracle-seed", "grassium-z"],
            ElementType.ICE: ["never-melt-ice", "icium-z"],
            ElementType.FIGHTING: ["black-belt", "fightinium-z"],
            ElementType.POISON: ["poison-barb", "poisonium-z"],
            ElementType.GROUND: ["soft-sand", "groundium-z"],
            ElementType.FLYING: ["sharp-beak", "flyinium-z"],
            ElementType.PSYCHIC: ["twisted-spoon", "psychium-z"],
            ElementType.BUG: ["silver-powder", "buginium-z"],
            ElementType.ROCK: ["hard-stone", "rockium-z"],
            ElementType.GHOST: ["spell-tag", "ghostium-z"],
            ElementType.DRAGON: ["dragon-fang", "dragonium-z"],
            ElementType.DARK: ["black-glasses", "darkinium-z"],
            ElementType.STEEL: ["metal-coat", "steelium-z"],
            ElementType.FAIRY: ["fairy-feather", "fairium-z"],
        }

        if move_type in type_items and self.get() in type_items[move_type]:
            multiplier *= 1.2

        # Life Orb (1.3x damage to all moves)
        if self.get() == "life-orb":
            multiplier *= 1.3

        # Expert Belt (1.2x damage to super effective moves)
        if self.get() == "expert-belt" and is_super_effective:
            multiplier *= 1.2

        # Choice items (1.5x damage)
        if self.get() == "choice-band" and move and move.damage_class == 2:  # PHYSICAL
            multiplier *= 1.5
        elif self.get() == "choice-specs" and move and move.damage_class == 3:  # SPECIAL
            multiplier *= 1.5

        # Metronome item
        if self.get() == "metronome" and move:
            multiplier *= self.owner.metronome.get_buff(move.name)

        return multiplier

    def get_defensive_multiplier(self, move_type, is_super_effective=False):
        """Get defensive multiplier for items that reduce damage taken."""
        multiplier = 1.0

        # Type-resist berries (0.5x damage from super effective moves once)
        resist_berries = {
            ElementType.NORMAL: "chilan-berry",
            ElementType.FIRE: "occa-berry",
            ElementType.WATER: "passho-berry",
            ElementType.ELECTRIC: "wacan-berry",
            ElementType.GRASS: "rindo-berry",
            ElementType.ICE: "yache-berry",
            ElementType.FIGHTING: "chople-berry",
            ElementType.POISON: "kebia-berry",
            ElementType.GROUND: "shuca-berry",
            ElementType.FLYING: "coba-berry",
            ElementType.PSYCHIC: "payapa-berry",
            ElementType.BUG: "tanga-berry",
            ElementType.ROCK: "charti-berry",
            ElementType.GHOST: "kasib-berry",
            ElementType.DRAGON: "haban-berry",
            ElementType.DARK: "colbur-berry",
            ElementType.STEEL: "babiri-berry",
            ElementType.FAIRY: "roseli-berry",
        }

        if move_type in resist_berries and self.get() == resist_berries[move_type] and is_super_effective:
            multiplier *= 0.5
            self.use()  # Consumed after use

        return multiplier

    def activate_on_damage(self, damage_taken, attacker=None, move=None, battle=None):
        """Activate item effects when taking damage. Returns formatted message."""
        msg = ""

        # Focus Sash/Focus Band - survive KO with 1 HP
        if damage_taken >= self.owner.hp and self.owner.hp == self.owner.starting_hp:
            if self.get() == "focus-sash":
                msg += f"{self.owner.name} held on with its Focus Sash!\n"
                self.owner.hp = 1
                self.use()
                return msg
            elif self.get() == "focus-band" and random.randint(1, 10) == 1:  # 10% chance
                msg += f"{self.owner.name} held on with its Focus Band!\n"
                self.owner.hp = 1
                return msg

        # Weakness Policy - boost Attack and Sp. Attack when hit by super effective move
        if self.get() == "weakness-policy" and move and attacker and hasattr(move, 'is_super_effective'):
            if move.is_super_effective:
                msg += self.owner.append_attack(2, attacker=attacker, source="its Weakness Policy")
                msg += self.owner.append_spatk(2, attacker=attacker, source="its Weakness Policy")
                self.use()

        # Air Balloon - pop when hit by any attack
        if self.get() == "air-balloon" and attacker and move:
            msg += f"{self.owner.name}'s Air Balloon popped!\n"
            self.use()

        # Rocky Helmet - deal 1/6 damage to attacker on contact
        if self.get() == "rocky-helmet" and attacker and move and hasattr(move, 'makes_contact') and move.makes_contact(
                attacker):
            recoil_damage = attacker.starting_hp // 6
            msg += attacker.damage(recoil_damage, battle, source=f"{self.owner.name}'s Rocky Helmet")

        # Jaboca Berry - deal damage when hit by physical move
        if self.get() == "jaboca-berry" and move and move.damage_class == 2 and attacker:  # PHYSICAL
            berry_damage = attacker.starting_hp // 8
            msg += attacker.damage(berry_damage, battle, source=f"{self.owner.name}'s Jaboca Berry")
            self.use()

        # Rowap Berry - deal damage when hit by special move
        if self.get() == "rowap-berry" and move and move.damage_class == 3 and attacker:  # SPECIAL
            berry_damage = attacker.starting_hp // 8
            msg += attacker.damage(berry_damage, battle, source=f"{self.owner.name}'s Rowap Berry")
            self.use()

        # Red Card - force attacker to switch out
        if self.get() == "red-card" and attacker and move and hasattr(move, 'makes_contact') and move.makes_contact(
                attacker):
            if not attacker.substitute:
                msg += f"{attacker.name} was forced to switch by the Red Card!\n"
                attacker.owner.mid_turn_remove = True
                self.use()

        # Eject Button - force self to switch out when hit
        if self.get() == "eject-button" and attacker and move:
            msg += f"{self.owner.name} is forced to switch by its Eject Button!\n"
            self.owner.owner.mid_turn_remove = True
            self.use()

        return msg

    def activate_end_of_turn(self, battle=None):
        """Activate item effects at end of turn. Returns formatted message."""
        msg = ""

        # Leftovers - heal 1/16 HP
        if self.get() == "leftovers" and self.owner.hp > 0 and self.owner.hp < self.owner.starting_hp:
            heal_amount = max(1, self.owner.starting_hp // 16)
            msg += self.owner.heal(heal_amount, source="its Leftovers")

        # Black Sludge - heal Poison types, hurt others
        elif self.get() == "black-sludge":
            if ElementType.POISON in self.owner.type_ids:
                if self.owner.hp > 0 and self.owner.hp < self.owner.starting_hp:
                    heal_amount = max(1, self.owner.starting_hp // 16)
                    msg += self.owner.heal(heal_amount, source="its Black Sludge")
            else:
                damage_amount = max(1, self.owner.starting_hp // 8)
                msg += self.owner.damage(damage_amount, battle, source="its Black Sludge")

        # Toxic Orb - badly poison holder
        elif self.get() == "toxic-orb" and not self.owner.nv.poison():
            msg += self.owner.nv.apply_status("b-poison", battle, attacker=self.owner, source="its Toxic Orb")

        # Flame Orb - burn holder
        elif self.get() == "flame-orb" and not self.owner.nv.burn():
            msg += self.owner.nv.apply_status("burn", battle, attacker=self.owner, source="its Flame Orb")

        # White Herb - restore negative stat changes
        elif self.get() == "white-herb":
            restored = False
            if self.owner.attack_stage < 0:
                self.owner.attack_stage = 0
                restored = True
            if self.owner.defense_stage < 0:
                self.owner.defense_stage = 0
                restored = True
            if self.owner.spatk_stage < 0:
                self.owner.spatk_stage = 0
                restored = True
            if self.owner.spdef_stage < 0:
                self.owner.spdef_stage = 0
                restored = True
            if self.owner.speed_stage < 0:
                self.owner.speed_stage = 0
                restored = True
            if self.owner.accuracy_stage < 0:
                self.owner.accuracy_stage = 0
                restored = True
            if self.owner.evasion_stage < 0:
                self.owner.evasion_stage = 0
                restored = True

            if restored:
                msg += f"{self.owner.name}'s White Herb restored its stats!\n"
                self.use()

        # Life Orb recoil
        if self.get() == "life-orb" and hasattr(self.owner,
                                                'used_damaging_move_this_turn') and self.owner.used_damaging_move_this_turn:
            if self.owner.hp > 0 and not (self.owner.ability() == Ability.MAGIC_GUARD):
                recoil = max(1, self.owner.starting_hp // 10)
                msg += self.owner.damage(recoil, battle, source="Life Orb recoil")

        return msg

    def eat_berry(self, *, consumer=None, attacker=None, move=None):
        """
        Eat this held item berry.

        Returns a formatted message.
        """
        msg = ""
        if not self.is_berry():
            return ""
        if consumer is None:
            consumer = self.owner
        else:
            msg += f"{consumer.name} eats {self.owner.name}'s berry!\n"

        # 2x or 1x
        ripe = int(consumer.ability(attacker=attacker, move=move) == Ability.RIPEN) + 1
        flavor = None

        if self == "sitrus-berry":
            msg += consumer.heal((ripe * consumer.starting_hp) // 4, source="eating its berry")
        elif self == "oran-berry":
            msg += consumer.heal(ripe * 10, source="eating its berry")
        elif self == "leppa-berry":
            # Restore 10 PP to a random move
            moves_with_missing_pp = [m for m in consumer.moves if m.pp < m.starting_pp]
            if moves_with_missing_pp:
                move_to_restore = random.choice(moves_with_missing_pp)
                pp_restored = min(ripe * 10, move_to_restore.starting_pp - move_to_restore.pp)
                move_to_restore.pp += pp_restored
                msg += f"{consumer.name} restored {pp_restored} PP to {move_to_restore.pretty_name}!\n"
        elif self == "figy-berry":
            msg += consumer.heal((ripe * consumer.starting_hp) // 3, source="eating its berry")
            flavor = "spicy"
        elif self == "wiki-berry":
            msg += consumer.heal((ripe * consumer.starting_hp) // 3, source="eating its berry")
            flavor = "dry"
        elif self == "mago-berry":
            msg += consumer.heal((ripe * consumer.starting_hp) // 3, source="eating its berry")
            flavor = "sweet"
        elif self == "aguav-berry":
            msg += consumer.heal((ripe * consumer.starting_hp) // 3, source="eating its berry")
            flavor = "bitter"
        elif self == "iapapa-berry":
            msg += consumer.heal((ripe * consumer.starting_hp) // 3, source="eating its berry")
            flavor = "sour"
        elif self == "apicot-berry":
            msg += consumer.append_spdef(ripe * 1, attacker=attacker, move=move, source="eating its berry")
        elif self == "ganlon-berry":
            msg += consumer.append_defense(ripe * 1, attacker=attacker, move=move, source="eating its berry")
        elif self == "lansat-berry":
            consumer.lansat_berry_ate = True
            msg += f"{consumer.name} is powered up by eating its berry.\n"
        elif self == "liechi-berry":
            msg += consumer.append_attack(ripe * 1, attacker=attacker, move=move, source="eating its berry")
        elif self == "micle-berry":
            consumer.micle_berry_ate = True
            msg += f"{consumer.name} is powered up by eating its berry.\n"
        elif self == "petaya-berry":
            msg += consumer.append_spatk(ripe * 1, attacker=attacker, move=move, source="eating its berry")
        elif self == "salac-berry":
            msg += consumer.append_speed(ripe * 1, attacker=attacker, move=move, source="eating its berry")
        elif self == "starf-berry":
            funcs = [
                consumer.append_attack,
                consumer.append_defense,
                consumer.append_spatk,
                consumer.append_spdef,
                consumer.append_speed,
            ]
            func = random.choice(funcs)
            msg += func(ripe * 2, attacker=attacker, move=move, source="eating its berry")
        elif self == "custap-berry":
            # Allows moving first in priority bracket next turn
            consumer.custap_berry_ate = True
            msg += f"{consumer.name} is powered up by eating its berry.\n"
        elif self == "aspear-berry":
            if consumer.nv.freeze():
                consumer.nv.reset()
                msg += f"{consumer.name} is no longer frozen after eating its berry!\n"
            else:
                msg += f"{consumer.name}'s berry had no effect!\n"
        elif self == "cheri-berry":
            if consumer.nv.paralysis():
                consumer.nv.reset()
                msg += f"{consumer.name} is no longer paralyzed after eating its berry!\n"
            else:
                msg += f"{consumer.name}'s berry had no effect!\n"
        elif self == "chesto-berry":
            if consumer.nv.sleep():
                consumer.nv.reset()
                msg += f"{consumer.name} woke up after eating its berry!\n"
            else:
                msg += f"{consumer.name}'s berry had no effect!\n"
        elif self == "pecha-berry":
            if consumer.nv.poison():
                consumer.nv.reset()
                msg += f"{consumer.name} is no longer poisoned after eating its berry!\n"
            else:
                msg += f"{consumer.name}'s berry had no effect!\n"
        elif self == "rawst-berry":
            if consumer.nv.burn():
                consumer.nv.reset()
                msg += f"{consumer.name} is no longer burned after eating its berry!\n"
            else:
                msg += f"{consumer.name}'s berry had no effect!\n"
        elif self == "persim-berry":
            if consumer.confusion.active():
                consumer.confusion.set_turns(0)
                msg += f"{consumer.name} is no longer confused after eating its berry!\n"
            else:
                msg += f"{consumer.name}'s berry had no effect!\n"
        elif self == "lum-berry":
            consumer.nv.reset()
            consumer.confusion.set_turns(0)
            msg += f"{consumer.name}'s statuses were cleared from eating its berry!\n"

        # Type resist berries are handled in get_defensive_multiplier

        if flavor is not None and consumer.disliked_flavor == flavor:
            msg += consumer.confuse(attacker=attacker, move=move, source="disliking its berry's flavor")
        if consumer.ability(attacker=attacker, move=move) == Ability.CHEEK_POUCH:
            msg += consumer.heal(consumer.starting_hp // 3, source="its cheek pouch")

        consumer.last_berry = self.item
        consumer.ate_berry = True
        if consumer.ability(attacker=attacker, move=move) == Ability.CUD_CHEW:
            consumer.cud_chew.set_turns(2)
        if consumer is self.owner:
            self.use()
        else:
            self.remove()

        return msg

    def get_speed_multiplier(self):
        """Get speed multiplier from held items."""
        multiplier = 1.0

        if self.get() == "choice-scarf":
            multiplier *= 1.5
        elif self.get() == "quick-powder" and self.owner._name == "Ditto":
            multiplier *= 2.0
        elif self.get() == "iron-ball":
            multiplier *= 0.5
        elif self.get() == "lagging-tail" or self.get() == "full-incense":
            # These make the holder move last in their priority bracket
            pass  # Handled in battle turn order logic
        elif self.get() == "power-anklet":
            multiplier *= 0.5
        elif self.get() == "macho-brace":
            multiplier *= 0.5

        return multiplier

    def get_stat_multiplier(self, stat):
        """Get stat multipliers from held items."""
        multiplier = 1.0

        # Eviolite - 1.5x Def/SpDef for Pokemon that can still evolve
        if self.get() == "eviolite" and self.owner.can_still_evolve:
            if stat in ("defense", "spdef"):
                multiplier *= 1.5

        # Assault Vest - 1.5x SpDef but prevents status moves
        elif self.get() == "assault-vest" and stat == "spdef":
            multiplier *= 1.5

        # Deep Sea Scale - 2x SpDef for Clamperl
        elif self.get() == "deep-sea-scale" and self.owner._name == "Clamperl" and stat == "spdef":
            multiplier *= 2.0

        # Deep Sea Tooth - 2x SpAtk for Clamperl
        elif self.get() == "deep-sea-tooth" and self.owner._name == "Clamperl" and stat == "spatk":
            multiplier *= 2.0

        # Light Ball - 2x Atk/SpAtk for Pikachu
        elif self.get() == "light-ball" and self.owner._name == "Pikachu":
            if stat in ("attack", "spatk"):
                multiplier *= 2.0

        # Thick Club - 2x Attack for Cubone/Marowak
        elif self.get() == "thick-club" and self.owner._name in ("Cubone", "Marowak", "Marowak-alola"):
            if stat == "attack":
                multiplier *= 2.0

        # Metal Powder - 2x Defense for Ditto
        elif self.get() == "metal-powder" and self.owner._name == "Ditto" and stat == "defense":
            multiplier *= 2.0

        return multiplier

    def activate_on_switch_in(self, battle=None):
        """Activate item effects when switching in. Returns formatted message."""
        msg = ""

        # Room Service - lower Speed in Trick Room
        if self.get() == "room-service" and battle and battle.trick_room.active():
            msg += self.owner.append_speed(-1, attacker=self.owner, source="its Room Service")
            self.use()

        # Booster Energy - activate Protosynthesis/Quark Drive
        if self.get() == "booster-energy" and not self.owner.booster_energy:
            if self.owner.ability() in (Ability.PROTOSYNTHESIS, Ability.QUARK_DRIVE):
                msg += f"{self.owner.name}'s Booster Energy activated its ability!\n"
                self.owner.booster_energy = True
                self.use()

        return msg

    def activate_on_move_use(self, move, battle=None):
        """Activate item effects when using a move. Returns formatted message."""
        msg = ""

        # Throat Spray - boost Sp. Attack when using sound move
        if self.get() == "throat-spray" and hasattr(move, 'is_sound_based') and move.is_sound_based():
            msg += self.owner.append_spatk(1, attacker=self.owner, source="its Throat Spray")
            self.use()

        return msg

    def __eq__(self, other):
        return self.get() == other

    def __getattr__(self, attr):
        if attr not in ("name", "power", "id", "effect"):
            raise AttributeError(f"{attr} is not an attribute of {self.__class__.__name__}.")
        if self.item is None:
            return None
        if attr == "name":
            return self.item.name
        if attr == "power":
            return self.item.power
        if attr == "id":
            return self.item.id
        if attr == "effect":
            return self.item.effect
        raise AttributeError(f"{attr} is not an attribute of {self.__class__.__name__}.")


class BatonPass():
    """Stores the necessary data from a pokemon to baton pass to another pokemon."""

    def __init__(self, poke):
        self.attack_stage = poke.attack_stage
        self.defense_stage = poke.defense_stage
        self.spatk_stage = poke.spatk_stage
        self.spdef_stage = poke.spdef_stage
        self.speed_stage = poke.speed_stage
        self.evasion_stage = poke.evasion_stage
        self.accuracy_stage = poke.accuracy_stage
        self.confusion = poke.confusion
        self.focus_energy = poke.focus_energy
        self.mind_reader = poke.mind_reader
        self.leech_seed = poke.leech_seed
        self.curse = poke.curse
        self.substitute = poke.substitute
        self.ingrain = poke.ingrain
        self.power_trick = poke.power_trick
        self.power_shift = poke.power_shift
        self.heal_block = poke.heal_block
        self.embargo = poke.embargo
        self.perish_song = poke.perish_song
        self.magnet_rise = poke.magnet_rise
        self.aqua_ring = poke.aqua_ring
        self.telekinesis = poke.telekinesis

    def apply(self, poke):
        """Push this objects data to a poke."""
        if poke.ability() != Ability.CURIOUS_MEDICINE:
            poke.attack_stage = self.attack_stage
            poke.defense_stage = self.defense_stage
            poke.spatk_stage = self.spatk_stage
            poke.spdef_stage = self.spdef_stage
            poke.speed_stage = self.speed_stage
            poke.evasion_stage = self.evasion_stage
            poke.accuracy_stage = self.accuracy_stage
        poke.confusion = self.confusion
        poke.focus_energy = self.focus_energy
        poke.mind_reader = self.mind_reader
        poke.leech_seed = self.leech_seed
        poke.curse = self
        poke.substitute = self.substitute
        poke.ingrain = self.ingrain
        poke.power_trick = self.power_trick
        poke.power_shift = self.power_shift
        poke.heal_block = self.heal_block
        poke.embargo = self.embargo
        poke.perish_song = self.perish_song
        poke.magnet_rise = self.magnet_rise
        poke.aqua_ring = self.aqua_ring
        poke.telekinesis = self.telekinesis
