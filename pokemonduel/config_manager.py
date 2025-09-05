import json
from typing import Any, Dict
from pathlib import Path


class MemberConfig:
    """Handles member-specific configuration data"""

    def __init__(self, config_manager, member_id: int):
        self.config_manager = config_manager
        self.member_id = member_id
        self._filepath = self.config_manager.data_dir / f"member_{member_id}.json"

    async def _load_data(self) -> Dict[str, Any]:
        """Load member data from file"""
        if not self._filepath.exists():
            return {}

        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    async def _save_data(self, data: Dict[str, Any]):
        """Save member data to file"""
        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def party(self):
        """Get party data - equivalent to config.member(player).party()"""
        data = await self._load_data()
        return data.get('party', self.config_manager.member_defaults.get('party', []))

    async def all(self) -> Dict[str, Any]:
        """Get all member data - equivalent to config.member().all()"""
        data = await self._load_data()
        # Apply defaults for missing keys
        result = self.config_manager.member_defaults.copy()
        result.update(data)
        return result

    async def set(self, key: str, value: Any):
        """Set a specific key - equivalent to config.member().key.set(value)"""
        data = await self._load_data()
        data[key] = value
        await self._save_data(data)

    async def get(self, key: str, default: Any = None):
        """Get a specific key with optional default"""
        data = await self._load_data()
        return data.get(key, self.config_manager.member_defaults.get(key, default))


class GuildConfig:
    """Handles guild-specific configuration data"""

    def __init__(self, config_manager, guild_id: int):
        self.config_manager = config_manager
        self.guild_id = guild_id
        self._filepath = self.config_manager.data_dir / f"guild_{guild_id}.json"

    async def _load_data(self) -> Dict[str, Any]:
        """Load guild data from file"""
        if not self._filepath.exists():
            return {}

        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    async def _save_data(self, data: Dict[str, Any]):
        """Save guild data to file"""
        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def useThreads(self):
        """Get useThreads setting - equivalent to config.guild().useThreads()"""
        data = await self._load_data()
        return data.get('useThreads', self.config_manager.guild_defaults.get('useThreads', False))

    async def all(self) -> Dict[str, Any]:
        """Get all guild data - equivalent to config.guild().all()"""
        data = await self._load_data()
        # Apply defaults for missing keys
        result = self.config_manager.guild_defaults.copy()
        result.update(data)
        return result

    async def set(self, key: str, value: Any):
        """Set a specific key"""
        data = await self._load_data()
        data[key] = value
        await self._save_data(data)

    async def get(self, key: str, default: Any = None):
        """Get a specific key with optional default"""
        data = await self._load_data()
        return data.get(key, self.config_manager.guild_defaults.get(key, default))


class ConfigManager:
    """
    Replacement for RedBot's Config system
    Provides the same functionality without RedBot dependency
    """

    def __init__(self, cog_name: str, identifier: int = None):
        self.cog_name = cog_name
        self.identifier = identifier

        # Create data directory
        self.data_dir = Path("data") / cog_name
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Store default values
        self.member_defaults = {}
        self.guild_defaults = {}

    def register_member(self, **kwargs):
        """
        Equivalent to config.register_member()
        Registers default values for member data
        """
        self.member_defaults.update(kwargs)

    def register_guild(self, **kwargs):
        """
        Equivalent to config.register_guild()
        Registers default values for guild data
        """
        self.guild_defaults.update(kwargs)

    def member(self, member):
        """
        Equivalent to config.member(member)
        Returns a MemberConfig instance for the given member
        """
        # Handle both Member objects and IDs
        member_id = getattr(member, 'id', member)
        return EnhancedMemberConfig(self, member_id)

    def guild(self, guild):
        """
        Equivalent to config.guild(guild)
        Returns a GuildConfig instance for the given guild
        """
        # Handle both Guild objects and IDs
        guild_id = getattr(guild, 'id', guild)
        return EnhancedGuildConfig(self, guild_id)

    @classmethod
    def get_conf(cls, cog, identifier: int):
        """
        Equivalent to Config.get_conf(self, identifier=id)
        Returns a ConfigManager instance
        """
        return cls(cog.__class__.__name__, identifier)


# Helper classes for attribute syntax
class PartyAttribute:
    """Helper class to handle party().set() syntax"""

    def __init__(self, member_config):
        self.member_config = member_config

    async def set(self, value):
        """Set party data - equivalent to config.member().party.set(value)"""
        await self.member_config.set('party', value)

    async def __call__(self):
        """Get party data when called - equivalent to config.member().party()"""
        # Call the actual party method from MemberConfig, not this class
        return await self.member_config._get_party_data()


class UseThreadsAttribute:
    """Helper class to handle useThreads().set() syntax"""

    def __init__(self, guild_config):
        self.guild_config = guild_config

    async def set(self, value):
        """Set useThreads data - equivalent to config.guild().useThreads.set(value)"""
        await self.guild_config.set('useThreads', value)

    async def __call__(self):
        """Get useThreads data when called - equivalent to config.guild().useThreads()"""
        # Call the actual useThreads method from GuildConfig, not this class
        return await self.guild_config._get_useThreads_data()


class EnhancedMemberConfig(MemberConfig):
    """Enhanced member config with attribute syntax support"""

    async def _get_party_data(self):
        """Internal method to get party data without recursion"""
        data = await self._load_data()
        return data.get('party', self.config_manager.member_defaults.get('party', []))

    @property
    def party(self):
        """Return PartyAttribute for .party syntax"""
        return PartyAttribute(self)


class EnhancedGuildConfig(GuildConfig):
    """Enhanced guild config with attribute syntax support"""

    async def _get_useThreads_data(self):
        """Internal method to get useThreads data without recursion"""
        data = await self._load_data()
        return data.get('useThreads', self.config_manager.guild_defaults.get('useThreads', False))

    @property
    def useThreads(self):
        """Return UseThreadsAttribute for .useThreads syntax"""
        return UseThreadsAttribute(self)


# Use EnhancedConfigManager as the main export
class EnhancedConfigManager(ConfigManager):
    """Main config manager with enhanced syntax support"""
    pass
