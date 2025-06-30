#!/usr/bin/env python3

"""
Pokemon Quetzal/Emerald Save File Parser

This parser analyzes save files from Pokemon Emerald-based ROM hack Quetzal.
"""

import struct
import ctypes
import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple, Any

# Rich imports for beautiful terminal output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

# Save file structure constants
SECTOR_SIZE = 4096
SECTOR_DATA_SIZE = 3968
SECTOR_FOOTER_SIZE = 12
SAVEBLOCK1_SIZE = SECTOR_DATA_SIZE * 4
SAVEBLOCK2_SIZE = SECTOR_DATA_SIZE
EMERALD_SIGNATURE = 0x08012025
VANILLA_POKEMON_NAME_LENGTH = 10
PLAYER_NAME_LENGTH = 7

# Pokémon Quetzal uses 18 sectors per slot instead of 14
SECTORS_PER_SLOT = 18
TOTAL_SECTORS = 32

# Party Pokemon constants (for this save file format)
PARTY_START_OFFSET = 0x6A8
PARTY_POKEMON_SIZE = 104
MAX_PARTY_SIZE = 6

# Default paths and offsets
DEFAULT_SAVE_PATH = "./save/player1.sav"

# Simple JSON data loading functions
_move_data: Dict[int, str] = {}
_species_data: Dict[int, str] = {}
_char_map: Dict[int, str] = {}
_nature_data: Dict[int, str] = {}

def _load_pokemon_data():
    """Load Pokemon data from JSON files"""
    global _move_data, _species_data, _char_map, _nature_data
    
    for filename, data_dict in [
        ("pokemon_moves.json", "_move_data"), 
        ("pokemon_species.json", "_species_data"),
        ("pokemon_charmap.json", "_char_map"),
        ("pokemon_natures.json", "_nature_data")
    ]:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                globals()[data_dict] = {int(k): v for k, v in json.load(f).items()}
        except FileNotFoundError:
            pass  # File doesn't exist, keep empty dict
        except Exception as e:
            print(f"[WARNING] Could not load {filename}: {e}")

# Load data once at module import time
_load_pokemon_data()

def get_move_name(move_id: int) -> str:
    """Get move name by ID"""
    return _move_data.get(move_id, f"Move {move_id}")

def get_species_name(speciesId: int) -> str:
    """Get species name by ID"""
    return _species_data.get(speciesId, f"Species {speciesId}")

def get_char_map() -> Dict[int, str]:
    """Get the loaded character map"""
    return _char_map

def get_nature_name(nature_id: int) -> str:
    """Get nature name by ID"""
    return _nature_data.get(nature_id, f"Nature {nature_id}")


class SaveBlock2(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("playerName", ctypes.c_uint8 * 8),
        ("padding_08", ctypes.c_uint8 * 8),
        ("playTimeHours", ctypes.c_uint32),
        ("playTimeMinutes", ctypes.c_uint8),
        ("playTimeSeconds", ctypes.c_uint8),
    ]

class PokemonData(ctypes.Structure):
    """Pokemon data structure for Pokemon Quetzal ROM hack (104 bytes total)."""
    _pack_ = 1
    _fields_ = [
        ("personality", ctypes.c_uint32),           # 0x00
        ("otId", ctypes.c_uint32),                  # 0x04
        ("nickname", ctypes.c_uint8 * 10),          # 0x08
        ("unknown_12", ctypes.c_uint8 * 2),         # 0x12
        ("otName", ctypes.c_uint8 * 7),             # 0x14
        ("unknown_1B", ctypes.c_uint8 * 8),         # 0x1B
        ("currentHp", ctypes.c_uint16),             # 0x23
        ("unknown_25", ctypes.c_uint8 * 3),         # 0x25
        ("speciesId", ctypes.c_uint16),             # 0x28
        ("item", ctypes.c_uint16),                  # 0x2A
        ("unknown_2C", ctypes.c_uint8 * 8),         # 0x2C
        ("move1", ctypes.c_uint16),                 # 0x34
        ("move2", ctypes.c_uint16),                 # 0x36
        ("move3", ctypes.c_uint16),                 # 0x38
        ("move4", ctypes.c_uint16),                 # 0x3A
        ("pp1", ctypes.c_uint8),                    # 0x3C
        ("pp2", ctypes.c_uint8),                    # 0x3D
        ("pp3", ctypes.c_uint8),                    # 0x3E
        ("pp4", ctypes.c_uint8),                    # 0x3F
        ("hpEV", ctypes.c_uint8),                   # 0x40
        ("atkEV", ctypes.c_uint8),                  # 0x41
        ("defEV", ctypes.c_uint8),                  # 0x42
        ("speEV", ctypes.c_uint8),                  # 0x43
        ("spaEV", ctypes.c_uint8),                  # 0x44
        ("spdEV", ctypes.c_uint8),                  # 0x45
        ("unknown_46", ctypes.c_uint8 * 10),        # 0x46
        ("ivData", ctypes.c_uint32),                # 0x50
        ("unknown_54", ctypes.c_uint8 * 4),         # 0x54
        ("level", ctypes.c_uint8),                  # 0x58
        ("unknown_59", ctypes.c_uint8),             # 0x59
        ("maxHp", ctypes.c_uint16),                 # 0x5A
        ("attack", ctypes.c_uint16),                # 0x5C
        ("defense", ctypes.c_uint16),               # 0x5E
        ("speed", ctypes.c_uint16),                 # 0x60
        ("spAttack", ctypes.c_uint16),              # 0x62
        ("spDefense", ctypes.c_uint16),             # 0x64
        ("unknown_66", ctypes.c_uint8 * 2),         # 0x66
    ]
    
    # Type annotation for raw_bytes attribute that gets added dynamically
    raw_bytes: bytes
    
    @property
    def nature_str(self) -> str:
        nature_index = (self.personality & 0xFF) % 25
        return get_nature_name(nature_index)
    
    @property
    def otName_str(self) -> str:
        return PokemonSaveParser.decode_pokemon_string(bytes(self.otName))

    @property
    def otId_str(self) -> str:
        return f"{self.otId & 0xFFFF:05}"
    
    @property
    def nickname_str(self) -> str:
        return PokemonSaveParser.decode_pokemon_string(bytes(self.nickname))

    @property
    def species_name(self) -> str:
        return get_species_name(self.speciesId)
    
    @property
    def moves(self) -> List[int]:
        return [self.move1, self.move2, self.move3, self.move4]
    
    @property
    def moves_from_substruct(self) -> List[int]:
        """Legacy method for backward compatibility."""
        return self.moves
    
    @property
    def evs(self) -> List[int]:
        """Returns [HP, Attack, Defense, Speed, Sp.Attack, Sp.Defense]"""
        return [self.hpEV, self.atkEV, self.defEV, self.speEV, self.spaEV, self.spdEV]
    
    @property
    def ivs(self) -> List[int]:
        """Returns [HP, Attack, Defense, Speed, Sp. Attack, Sp. Defense]"""
        iv_data = self.ivData
        return [
            iv_data & 0x1F,           # HP
            (iv_data >> 5) & 0x1F,    # Attack
            (iv_data >> 10) & 0x1F,   # Defense
            (iv_data >> 15) & 0x1F,   # Speed
            (iv_data >> 20) & 0x1F,   # Sp. Attack
            (iv_data >> 25) & 0x1F,   # Sp. Defense
        ]
    
    @property
    def move_names(self) -> List[str]:
        return [get_move_name(move_id) if move_id != 0 else "---" for move_id in self.moves]

    @property
    def pp_values(self) -> List[int]:
        return [self.pp1, self.pp2, self.pp3, self.pp4]
    


class SectorInfo(NamedTuple):
    id: int
    checksum: int
    counter: int
    valid: bool


class PokemonSaveParser:
    """Pokemon Quetzal ROM hack save file parser."""
    
    def __init__(self, save_path: str, forced_slot: Optional[int] = None):
        self.save_path = Path(save_path)
        self.save_data: Optional[bytes] = None
        self.active_slot_start: int = 0
        self.sector_map: Dict[int, int] = {}
        self.forced_slot = forced_slot  # None for auto-detect, 1 for slot 1, 2 for slot 2

    def load_save_file(self) -> None:
        if not self.save_path.exists():
            raise FileNotFoundError(f"Save file not found: {self.save_path}")
        try:
            with open(self.save_path, "rb") as f:
                self.save_data = f.read()
        except IOError as e:
            raise IOError(f"Failed to read save file: {e}")

    @staticmethod
    def decode_pokemon_string(encoded_bytes: bytes) -> str:
        result = ""
        char_map = get_char_map()
        for byte in encoded_bytes:
            if byte == 0xFF:  # Terminator
                break
            result += char_map.get(byte, "?")
        return result

    def get_sector_info(self, sector_index: int) -> SectorInfo:
        if not self.save_data:
            raise ValueError("Save data not loaded")
        
        # Calculate the footer offset
        footer_offset = (sector_index * SECTOR_SIZE) + SECTOR_SIZE - SECTOR_FOOTER_SIZE
        
        if footer_offset + SECTOR_FOOTER_SIZE > len(self.save_data):
            return SectorInfo(-1, 0, 0, False)
            
        try:
            # Extract footer data: id (u16), checksum (u16), signature (u32), counter (u32)
            sector_id, checksum, signature, counter = struct.unpack(
                "<HHII",
                self.save_data[footer_offset:footer_offset + SECTOR_FOOTER_SIZE]
            )
            
            # Check signature first
            if signature != EMERALD_SIGNATURE:
                return SectorInfo(sector_id, checksum, counter, False)
            
            # Get sector data for checksum verification
            sector_start = sector_index * SECTOR_SIZE
            sector_data = self.save_data[sector_start:sector_start + SECTOR_DATA_SIZE]
            
            # Calculate checksum and verify
            calculated_checksum = self.calculate_sector_checksum(sector_data)
            valid = (calculated_checksum == checksum)
            
            return SectorInfo(sector_id, checksum, counter, valid)
        except (struct.error, IndexError):
            return SectorInfo(-1, 0, 0, False)

    def determine_active_slot(self) -> None:
        """Determine the active save slot based on highest counter or forced selection."""
        if self.forced_slot is not None:
            self.active_slot_start = 0 if self.forced_slot == 1 else 14
            return
        
        # Get highest counter from each slot
        slot1_counter = max((self.get_sector_info(i).counter for i in range(18) 
                            if self.get_sector_info(i).valid), default=0)
        slot2_counter = max((self.get_sector_info(i).counter for i in range(14, 32) 
                            if self.get_sector_info(i).valid), default=0)
        
        # Use slot with higher counter (slot 2 wins ties)
        self.active_slot_start = 14 if slot2_counter >= slot1_counter else 0

    def debug_save_slots(self) -> None:
        """Debug method to print information about both save slots."""
        print("\n--- Save Slot Debug Information ---")
        
        # Helper function to analyze a slot
        def analyze_slot(slot_range, slot_name):
            valid_sectors = []
            counters = []
            for i in slot_range:
                sector_info = self.get_sector_info(i)
                if sector_info.valid:
                    valid_sectors.append(i)
                    counters.append(sector_info.counter)
                    print(f"  Sector {i}: ID={sector_info.id}, Counter={sector_info.counter:08X}")
            
            max_counter = max(counters) if counters else 0
            print(f"{slot_name}: {len(valid_sectors)} valid sectors, max counter {max_counter:08X}")
            return len(valid_sectors), max_counter
        
        # Analyze both slots
        slot1_count, slot1_counter = analyze_slot(range(18), "Slot 1 (sectors 0-17)")
        slot2_count, slot2_counter = analyze_slot(range(14, 32), "Slot 2 (sectors 14-31)")
        
        # Show active slot decision
        active_slot = 14 if slot2_counter >= slot1_counter else 0
        print(f"\nActive slot: {active_slot} (highest counter wins, slot 2 wins ties)")

    def build_sector_map(self) -> None:
        """
        Build sector map for the active slot.
        If a forced slot is specified, prioritize that slot but allow recovery from the other slot.
        Otherwise, use sectors with the highest counter and recover missing sectors.
        """
        self.sector_map = {}
        
        if self.forced_slot is not None:
            # Forced slot: prioritize specified slot but allow recovery
            primary_range = range(18) if self.forced_slot == 1 else range(14, 32)
            other_range = range(14, 32) if self.forced_slot == 1 else range(18)
            
            # Collect sectors from forced slot
            for i in primary_range:
                sector_info = self.get_sector_info(i)
                if sector_info.valid:
                    self.sector_map[sector_info.id] = i
            
            # Recover missing critical sectors from other slot
            missing_critical = [i for i in range(5) if i not in self.sector_map]
            for i in other_range:
                sector_info = self.get_sector_info(i)
                if sector_info.valid and sector_info.id in missing_critical:
                    self.sector_map[sector_info.id] = i
                    missing_critical.remove(sector_info.id)
            
            if missing_critical:
                print(f"[WARNING] Missing critical sectors: {missing_critical}")
                
        else:
            # Auto-detection mode: use sectors with highest counters
            all_sectors = {}  # sector_id -> (physical_sector, counter)
            
            for i in range(32):
                sector_info = self.get_sector_info(i)
                if sector_info.valid:
                    sector_id = sector_info.id
                    if sector_id not in all_sectors or sector_info.counter > all_sectors[sector_id][1]:
                        all_sectors[sector_id] = (i, sector_info.counter)
            
            for sector_id, (physical_sector, counter) in all_sectors.items():
                self.sector_map[sector_id] = physical_sector
            
            missing_critical = [i for i in range(5) if i not in self.sector_map]
            if missing_critical:
                print(f"[ERROR] Missing critical sectors: {missing_critical}")

    def extract_saveblock1(self) -> bytearray:
        if not self.save_data:
            raise ValueError("Save data not loaded")
        
        saveblock1_sectors = [i for i in range(1, 5) if i in self.sector_map]
        if not saveblock1_sectors:
            raise ValueError("No SaveBlock1 sectors found")
        
        saveblock1_data = bytearray(SAVEBLOCK1_SIZE)
        for sector_id in saveblock1_sectors:
            sector_idx = self.sector_map[sector_id]
            start_offset = sector_idx * SECTOR_SIZE
            sector_data = self.save_data[start_offset:start_offset + SECTOR_DATA_SIZE]
            chunk_offset = (sector_id - 1) * SECTOR_DATA_SIZE
            saveblock1_data[chunk_offset:chunk_offset + SECTOR_DATA_SIZE] = sector_data[:SECTOR_DATA_SIZE]
        return saveblock1_data

    def extract_saveblock2(self) -> bytes:
        if not self.save_data:
            raise ValueError("Save data not loaded")
        if 0 not in self.sector_map:
            raise ValueError("SaveBlock2 sector (ID 0) not found")
        sector_idx = self.sector_map[0]
        start_offset = sector_idx * SECTOR_SIZE
        saveblock2_data = self.save_data[start_offset:start_offset + SECTOR_DATA_SIZE]
        return saveblock2_data

    def parse_party_pokemon(self, saveblock1_data: bytes) -> List[PokemonData]:
        party_pokemon: List[PokemonData] = []
        for slot in range(MAX_PARTY_SIZE):
            pokemon_offset = PARTY_START_OFFSET + slot * PARTY_POKEMON_SIZE
            pokemon_data = saveblock1_data[pokemon_offset:pokemon_offset + PARTY_POKEMON_SIZE]
            if len(pokemon_data) < PARTY_POKEMON_SIZE:
                break
            
            if len(pokemon_data) < ctypes.sizeof(PokemonData):
                break
            pokemon_struct = PokemonData.from_buffer_copy(pokemon_data[:ctypes.sizeof(PokemonData)])
            if pokemon_struct.speciesId == 0:
                break
            # Store raw bytes as an attribute for debugging
            pokemon_struct.raw_bytes = pokemon_data
            party_pokemon.append(pokemon_struct)
        return party_pokemon

    def parse_player_name(self, saveblock2_data: bytes) -> str:
        if len(saveblock2_data) < ctypes.sizeof(SaveBlock2):
            raise ValueError("SaveBlock2 data too small")
        saveblock2 = SaveBlock2.from_buffer_copy(saveblock2_data)
        player_name_bytes = bytes(saveblock2.playerName)
        return PokemonSaveParser.decode_pokemon_string(player_name_bytes)

    def parse_play_time(self, saveblock2_data: bytes) -> Dict[str, int]:
        if len(saveblock2_data) < ctypes.sizeof(SaveBlock2):
            raise ValueError("SaveBlock2 data too small")
        saveblock2 = SaveBlock2.from_buffer_copy(saveblock2_data)
        return {
            'hours': saveblock2.playTimeHours,
            'minutes': saveblock2.playTimeMinutes,
            'seconds': saveblock2.playTimeSeconds
        }

    def parse_save_file(self) -> Dict[str, Any]:
        self.load_save_file()
        self.determine_active_slot()
        self.build_sector_map()
        saveblock1_data = self.extract_saveblock1()
        saveblock2_data = self.extract_saveblock2()
        player_name = self.parse_player_name(saveblock2_data)
        party_pokemon = self.parse_party_pokemon(saveblock1_data)
        play_time = self.parse_play_time(saveblock2_data)
        return {
            'party_pokemon': party_pokemon,
            'player_name': player_name,
            'play_time': play_time,
            'active_slot': self.active_slot_start,
            'sector_map': self.sector_map
        }

    @staticmethod
    def display_party_pokemon(party_pokemon: List[PokemonData]) -> None:
        print("\n--- Party Pokémon Summary ---")
        if not party_pokemon:
            print("No Pokémon found in party.")
            return
        
        header = (
            f"{'Slot':<5}{'Dex ID':<8}{'Nickname':<12}{'Lv':<4}{'Nature':<10}"
            f"{'HP':<30} {'Atk':<5}{'Def':<5}{'Spe':<5}{'SpA':<5}{'SpD':<5}"
            f"{'OT Name':<10}{'IDNo':<7}"
        )
        print(header)
        print("-" * len(header))
        
        for slot, pokemon in enumerate(party_pokemon, 1):
            hp_percent = (pokemon.currentHp / pokemon.maxHp) if pokemon.maxHp > 0 else 0.0
            hp_bar_length = 20
            filled_bars = int(hp_bar_length * hp_percent)
            hp_bar = "█" * filled_bars + "░" * (hp_bar_length - filled_bars)
            hp_display = f"[{hp_bar}] {pokemon.currentHp}/{pokemon.maxHp}"
            
            print(
                f"{slot:<5}{pokemon.speciesId:<8}{pokemon.nickname_str:<12}{pokemon.level:<4}"
                f"{pokemon.nature_str:<10}{hp_display:<30} {pokemon.attack:<5}{pokemon.defense:<5}"
                f"{pokemon.speed:<5}{pokemon.spAttack:<5}{pokemon.spDefense:<5}"
                f"{pokemon.otName_str:<10}{pokemon.otId_str:<7}"
            )

    @staticmethod
    def display_saveblock2_info(save_data: Dict[str, Any]) -> None:
        print("\n--- SaveBlock2 Data ---")
        print(f"Player Name: {save_data['player_name']}")
        play_time = save_data['play_time']
        print(f"Play Time: {play_time['hours']}h {play_time['minutes']}m {save_data['play_time']['seconds']}s")

    @staticmethod
    def display_save_info(save_data: Dict[str, Any]) -> None:
        print(f"Active save slot: {save_data['active_slot']}")
        print(f"Valid sectors found: {len(save_data['sector_map'])}")
        PokemonSaveParser.display_party_pokemon(save_data['party_pokemon'])
        PokemonSaveParser.display_saveblock2_info(save_data)

    @staticmethod
    def display_party_pokemon_raw(party_pokemon: List[PokemonData]) -> None:
        print("\n--- Party Pokémon Raw Bytes ---")
        if not party_pokemon:
            print("No Pokémon found in party.")
            return
        for slot, pokemon in enumerate(party_pokemon, 1):
            nickname = PokemonSaveParser.decode_pokemon_string(bytes(pokemon.nickname))
            print(f"\n--- Slot {slot}: {nickname} ---")
            # Use the raw bytes stored during parsing
            print(' '.join(f'{b:02x}' for b in pokemon.raw_bytes))

    @staticmethod
    def pokemon_to_dict(pokemon: PokemonData) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        
        # Handle ctypes _fields_ which can be either 2-tuple or 3-tuple
        for field_info in pokemon._fields_:
            if len(field_info) >= 2:
                field_name = field_info[0]
                value = getattr(pokemon, field_name)
                
                if field_name in ["nickname", "otName"]:
                    data[field_name] = PokemonSaveParser.decode_pokemon_string(bytes(value))
                elif isinstance(value, ctypes.Array):
                    data[field_name] = [int(x) for x in value]
                else:
                    data[field_name] = int(value) if hasattr(value, '__int__') else value
                    
        data['displayOtId'] = pokemon.otId_str
        data['displayNature'] = pokemon.nature_str
        data['moves'] = pokemon.moves
        data['moveNames'] = pokemon.move_names
        data['ppValues'] = pokemon.pp_values
        data['evs'] = pokemon.evs
        data['ivs'] = pokemon.ivs
        data['totalEvs'] = sum(pokemon.evs)
        data['totalIvs'] = sum(pokemon.ivs)
        return data

    @staticmethod
    def display_json_output(save_data: Dict[str, Any]) -> None:
        party_pokemon_for_json: List[Dict[str, Any]] = [
            PokemonSaveParser.pokemon_to_dict(p) for p in save_data['party_pokemon']
        ]

        json_output: Dict[str, Any] = {
            'player_name': save_data['player_name'],
            'play_time': save_data['play_time'],
            'active_slot': save_data['active_slot'],
            'sector_map': save_data['sector_map'],
            'party_pokemon': party_pokemon_for_json
        }
        print(json.dumps(json_output))

    @staticmethod
    def display_party_pokemon_detailed(party_pokemon: List[PokemonData]) -> None:
        """Display party pokemon using rich formatting for beautiful output"""
        console = Console()
        
        if not party_pokemon:
            console.print(Panel("No Pokémon found in party.", title="Party", style="red"))
            return
        
        # Create main layout
        console.print("\n")
        console.print(Panel.fit("🎮 POKÉMON PARTY SUMMARY 🎮", style="bold magenta"))
        
        for slot, pokemon in enumerate(party_pokemon, 1):
            # Create individual pokemon panel
            
            # HP Bar
            hp_percent = (pokemon.currentHp / pokemon.maxHp) if pokemon.maxHp > 0 else 0.0
            if pokemon.currentHp == 0:
                hp_status = "[red]FAINTED[/red]"
            else:
                hp_status = "[green]HEALTHY[/green]"
            
            # Basic info table
            info_table = Table(show_header=False, box=box.SIMPLE)
            info_table.add_column("Field", style="cyan")
            info_table.add_column("Value", style="white")
            
            info_table.add_row("Species", f"{pokemon.species_name} (#{pokemon.speciesId})")
            info_table.add_row("Level", f"{pokemon.level}")
            info_table.add_row("Nature", f"[bold]{pokemon.nature_str}[/bold]")
            info_table.add_row("Trainer", f"{pokemon.otName_str} (ID: {pokemon.otId_str})")
            info_table.add_row("HP", f"{pokemon.currentHp}/{pokemon.maxHp} {hp_status}")
            
            # Stats table
            stats_table = Table(title="Base Stats", box=box.ROUNDED)
            stats_table.add_column("Stat", style="cyan")
            stats_table.add_column("Value", justify="right", style="yellow")
            
            stats_table.add_row("Attack", f"{pokemon.attack}")
            stats_table.add_row("Defense", f"{pokemon.defense}")
            stats_table.add_row("Speed", f"{pokemon.speed}")
            stats_table.add_row("Sp.Atk", f"{pokemon.spAttack}")
            stats_table.add_row("Sp.Defense", f"{pokemon.spDefense}")
            
            # Moves table
            moves_table = Table(title="Moves", box=box.ROUNDED)
            moves_table.add_column("#", width=3)
            moves_table.add_column("Move", style="green")
            moves_table.add_column("PP", justify="center", style="yellow")
            moves_table.add_column("ID", justify="right", style="dim")
            
            moves = pokemon.moves_from_substruct
            move_names = pokemon.move_names
            pp_values = pokemon.pp_values
            for i, (move_id, move_name, pp) in enumerate(zip(moves, move_names, pp_values), 1):
                if move_id > 0:
                    moves_table.add_row(f"{i}", move_name, f"{pp}", f"{move_id}")
                else:
                    moves_table.add_row(f"{i}", "[dim]---[/dim]", "[dim]---[/dim]", "[dim]---[/dim]")
            
            # EVs and IVs - use direct properties instead of substruct parsing
            iv_data_table = Table(title="Training Data", box=box.ROUNDED)
            iv_data_table.add_column("Type", style="cyan")
            iv_data_table.add_column("HP", justify="center")
            iv_data_table.add_column("Atk", justify="center") 
            iv_data_table.add_column("Def", justify="center")
            iv_data_table.add_column("Spe", justify="center")
            iv_data_table.add_column("SpA", justify="center")
            iv_data_table.add_column("SpD", justify="center")
            iv_data_table.add_column("Total", justify="center", style="bold")
            
            # Get EVs directly from the structure
            evs = pokemon.evs
            total_evs = sum(evs)
            ev_style = "green" if total_evs <= 510 else "red"
            iv_data_table.add_row(
                f"[{ev_style}]EVs[/{ev_style}]",
                f"[{ev_style}]{evs[0]}[/{ev_style}]",  # HP
                f"[{ev_style}]{evs[1]}[/{ev_style}]",  # Attack
                f"[{ev_style}]{evs[2]}[/{ev_style}]",  # Defense
                f"[{ev_style}]{evs[3]}[/{ev_style}]",  # Speed
                f"[{ev_style}]{evs[4]}[/{ev_style}]",  # Sp.Attack
                f"[{ev_style}]{evs[5]}[/{ev_style}]",  # Sp.Defense
                f"[{ev_style}]{total_evs}[/{ev_style}]"  # Total EVs
            )
            
            # Get IVs directly from the structure
            ivs = pokemon.ivs
            total_ivs = sum(ivs)
            
            # Color code IVs (31 is perfect)
            def iv_color(iv: int) -> str:
                if iv == 31:
                    return "bright_green"
                elif iv >= 25:
                    return "green" 
                elif iv >= 15:
                    return "yellow"
                else:
                    return "red"
            
            # Color code total IVs (186 is perfect = 31*6)
            def total_iv_color(total: int) -> str:
                if total == 186:
                    return "bright_green"
                elif total >= 155:  # ~25 average
                    return "green"
                elif total >= 93:   # ~15 average
                    return "yellow"
                else:
                    return "red"
            
            iv_data_table.add_row(
                "IVs",
                f"[{iv_color(ivs[0])}]{ivs[0]}[/{iv_color(ivs[0])}]",  # HP
                f"[{iv_color(ivs[1])}]{ivs[1]}[/{iv_color(ivs[1])}]",  # Attack
                f"[{iv_color(ivs[2])}]{ivs[2]}[/{iv_color(ivs[2])}]",  # Defense
                f"[{iv_color(ivs[3])}]{ivs[3]}[/{iv_color(ivs[3])}]",  # Speed
                f"[{iv_color(ivs[4])}]{ivs[4]}[/{iv_color(ivs[4])}]",  # Sp.Attack
                f"[{iv_color(ivs[5])}]{ivs[5]}[/{iv_color(ivs[5])}]",  # Sp.Defense
                f"[{total_iv_color(total_ivs)}]{total_ivs}[/{total_iv_color(total_ivs)}]"  # Total IVs
            )
            
            # Combine tables into columns
            left_column = Columns([info_table, stats_table], equal=True)
            right_column = Columns([moves_table, iv_data_table], equal=True)
            
            # Create the pokemon panel
            pokemon_panel = Panel(
                Columns([left_column, right_column], equal=True),
                title=f"[bold]Slot {slot}: {pokemon.nickname_str.upper()}[/bold]",
                border_style="blue"
            )
            
            console.print(pokemon_panel)
            console.print()

    def calculate_sector_checksum(self, sector_data: bytes) -> int:
        """Calculate sector checksum using the original game's algorithm."""
        if len(sector_data) < SECTOR_DATA_SIZE:
            return 0
            
        checksum = 0
        for i in range(0, SECTOR_DATA_SIZE, 4):
            if i + 4 <= len(sector_data):
                value = struct.unpack("<I", sector_data[i:i+4])[0]
                checksum += value
        
        return ((checksum >> 16) + (checksum & 0xFFFF)) & 0xFFFF

def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

    parser = argparse.ArgumentParser(description='Pokemon Quetzal ROM Hack Save File Parser')
    parser.add_argument('save_file', nargs='?', default=DEFAULT_SAVE_PATH,
                        help='Path to the save file (default: ./save/player1.sav)')
    parser.add_argument('--debugParty', action='store_true', help='Display raw party pokemon bytes')
    parser.add_argument('--debugSlots', action='store_true', help='Display save slot debug information')
    parser.add_argument('--detailed', action='store_true', help='Display detailed party pokemon information')
    parser.add_argument('--json', action='store_true', help='Return JSON instead of human readable table')
    
    slot_group = parser.add_mutually_exclusive_group()
    slot_group.add_argument('--slot1', action='store_true', help='Force load from save slot 1 (sectors 0-17)')
    slot_group.add_argument('--slot2', action='store_true', help='Force load from save slot 2 (sectors 14-31)')
    
    args = parser.parse_args()
    
    # Determine forced slot
    forced_slot = None
    if args.slot1:
        forced_slot = 1
    elif args.slot2:
        forced_slot = 2
    
    try:
        save_parser = PokemonSaveParser(args.save_file, forced_slot)
        
        if args.debugSlots:
            save_parser.load_save_file()
            save_parser.debug_save_slots()
            return
            
        save_data = save_parser.parse_save_file()
        if args.json:
            PokemonSaveParser.display_json_output(save_data)
        elif args.debugParty:
            PokemonSaveParser.display_party_pokemon_raw(save_data['party_pokemon'])
        elif args.detailed:
            PokemonSaveParser.display_party_pokemon_detailed(save_data['party_pokemon'])
        else:
            PokemonSaveParser.display_save_info(save_data)
    except (FileNotFoundError, IOError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()