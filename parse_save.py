#!/usr/bin/env python3

import struct
import ctypes
import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple, Any

# Save file structure constants
SECTOR_SIZE = 4096
SECTOR_DATA_SIZE = 3968
SECTOR_FOOTER_SIZE = 12
SAVEBLOCK1_SIZE = SECTOR_DATA_SIZE * 4
SAVEBLOCK2_SIZE = SECTOR_DATA_SIZE
EMERALD_SIGNATURE = 0x08012025
VANILLA_POKEMON_NAME_LENGTH = 10
PLAYER_NAME_LENGTH = 7

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

def get_species_name(species_id: int) -> str:
    """Get species name by ID"""
    return _species_data.get(species_id, f"Species {species_id}")

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


class PokemonSubstruct0(ctypes.Structure):
    """Growth data substruct (12 bytes)"""
    _pack_ = 1
    _fields_ = [
        ("species", ctypes.c_uint16),       # 0x00 - Species ID
        ("heldItem", ctypes.c_uint16),      # 0x02 - Held item
        ("experience", ctypes.c_uint32),    # 0x04 - Experience points
        ("ppBonuses", ctypes.c_uint8),      # 0x08 - PP bonuses
        ("friendship", ctypes.c_uint8),     # 0x09 - Friendship
        ("unknown", ctypes.c_uint16),       # 0x0A - Unknown/padding
    ]


class PokemonSubstruct1(ctypes.Structure):
    """Moves data substruct (12 bytes)"""
    _pack_ = 1
    _fields_ = [
        ("move1", ctypes.c_uint16),         # 0x00 - Move 1
        ("move2", ctypes.c_uint16),         # 0x02 - Move 2
        ("move3", ctypes.c_uint16),         # 0x04 - Move 3
        ("move4", ctypes.c_uint16),         # 0x06 - Move 4
        ("pp1", ctypes.c_uint8),            # 0x08 - PP for move 1
        ("pp2", ctypes.c_uint8),            # 0x09 - PP for move 2
        ("pp3", ctypes.c_uint8),            # 0x0A - PP for move 3
        ("pp4", ctypes.c_uint8),            # 0x0B - PP for move 4
    ]


class PokemonSubstruct2(ctypes.Structure):
    """EVs and Contest stats substruct (12 bytes)"""
    _pack_ = 1
    _fields_ = [
        ("hpEV", ctypes.c_uint8),           # 0x00 - HP EV
        ("attackEV", ctypes.c_uint8),       # 0x01 - Attack EV
        ("defenseEV", ctypes.c_uint8),      # 0x02 - Defense EV
        ("speedEV", ctypes.c_uint8),        # 0x03 - Speed EV
        ("spAttackEV", ctypes.c_uint8),     # 0x04 - Special Attack EV
        ("spDefenseEV", ctypes.c_uint8),    # 0x05 - Special Defense EV
        ("cool", ctypes.c_uint8),           # 0x06 - Cool contest stat
        ("beauty", ctypes.c_uint8),         # 0x07 - Beauty contest stat
        ("cute", ctypes.c_uint8),           # 0x08 - Cute contest stat
        ("smart", ctypes.c_uint8),          # 0x09 - Smart contest stat
        ("tough", ctypes.c_uint8),          # 0x0A - Tough contest stat
        ("sheen", ctypes.c_uint8),          # 0x0B - Sheen
    ]


class PokemonSubstruct3(ctypes.Structure):
    """Misc data substruct (12 bytes)"""
    _pack_ = 1
    _fields_ = [
        ("pokerus", ctypes.c_uint8),        # 0x00 - Pokerus
        ("metLocation", ctypes.c_uint8),    # 0x01 - Met location
        ("metLevelAndInfo", ctypes.c_uint16), # 0x02 - Met level and other info
        ("ivData", ctypes.c_uint32),        # 0x04 - IVs packed in 32-bit value
        ("ribbonsAndAbility", ctypes.c_uint32), # 0x08 - Ribbons and ability data
    ]


class PokemonData(ctypes.Structure):
    """
    Pokemon data structure for Pokemon Quetzal rom hack (104 bytes total).
    
    Based on actual data analysis of the save file format.
    This structure has been reverse-engineered from working save data.
    """
    _pack_ = 1
    _fields_ = [
        # Box Pokemon data - first part
        ("personality", ctypes.c_uint32),       # 0x00 - Personality value (32-bit)
        ("otId", ctypes.c_uint32),              # 0x04 - Original Trainer ID (32-bit)
        ("nickname", ctypes.c_uint8 * VANILLA_POKEMON_NAME_LENGTH),    # 0x08 - Pokemon nickname (10 bytes)
        ("language", ctypes.c_uint8),           # 0x12 - Language
        ("unknown_13", ctypes.c_uint8),         # 0x13 - Unknown data (1 byte)
        ("otName", ctypes.c_uint8 * PLAYER_NAME_LENGTH),  # 0x14 - OT Name (7 bytes) ✓ VERIFIED
        ("markings", ctypes.c_uint8),           # 0x1B - Markings
        ("checksum", ctypes.c_uint16),          # 0x1C - Checksum
        ("hpLost", ctypes.c_uint16),            # 0x1E - HP lost
        ("unknown_20", ctypes.c_uint8 * 3),     # 0x20 - Unknown data (3 bytes)
        ("actualCurrentHp", ctypes.c_uint16),   # 0x23 - Actual current HP ✓ VERIFIED
        ("unknown_25", ctypes.c_uint8 * 3),     # 0x25 - Unknown data (3 bytes)
        ("species_id", ctypes.c_uint16),        # 0x28 - Species ID ✓ VERIFIED at offset 40
        ("unknown_2A", ctypes.c_uint8 * 42),    # 0x2A - Unknown/encrypted data (42 bytes)
        
        # Party-specific data starts around 0x54
        ("currentHp", ctypes.c_uint16),         # 0x54 - Current HP (0 for fainted, needs calculation for healthy)
        ("unknown_56", ctypes.c_uint8 * 2),     # 0x56 - Unknown (2 bytes)
        ("level", ctypes.c_uint8),              # 0x58 - Pokemon level ✓ VERIFIED at offset 88
        ("unknown_59", ctypes.c_uint8),         # 0x59 - Unknown (1 byte)
        ("maxHp", ctypes.c_uint16),             # 0x5A - Max HP ✓ VERIFIED at offset 90
        ("attack", ctypes.c_uint16),            # 0x5C - Attack ✓ VERIFIED at offset 92
        ("defense", ctypes.c_uint16),           # 0x5E - Defense ✓ VERIFIED at offset 94
        ("speed", ctypes.c_uint16),             # 0x60 - Speed ✓ VERIFIED at offset 96
        ("spAttack", ctypes.c_uint16),          # 0x62 - Sp.Attack ✓ VERIFIED at offset 98
        ("spDefense", ctypes.c_uint16),         # 0x64 - Sp.Defense ✓ VERIFIED at offset 100
        ("unknown_66", ctypes.c_uint8 * 2),     # 0x66 - Unknown (2 bytes to reach 104 total)
    ]
    
    # Type annotation for raw_bytes attribute that gets added dynamically
    raw_bytes: bytes
    
    @property
    def nature_str(self) -> str:
        # Nature is derived from personality value mod 25
        nature_index = self.personality % 25
        return get_nature_name(nature_index)
    
    @property
    def otName_str(self) -> str:
        # Decode the OT name from the structure data
        return PokemonSaveParser.decode_pokemon_string(bytes(self.otName))

    @property
    def otId_str(self) -> str:
        # Returns the lower 16 bits of otId as a zero-padded 5-digit string
        return f"{self.otId & 0xFFFF:05}"
    
    @property
    def nickname_str(self) -> str:
        # Decode the nickname bytes to a string
        return PokemonSaveParser.decode_pokemon_string(bytes(self.nickname))

    @property
    def species_name(self) -> str:
        """Get the species name for this Pokemon"""
        return get_species_name(self.species_id)

    @property
    def effective_current_hp(self) -> int:
        """
        Return the actual current HP.
        The correct current HP is stored at offset 0x23 (actualCurrentHp field).
        """
        return self.actualCurrentHp

    def decrypt_substruct_data(self) -> bytes:
        """
        Decrypt the Pokemon substruct data using the same algorithm as the C code.
        Returns 48 bytes of decrypted substruct data (4 substructs * 12 bytes each).
        """
        if not hasattr(self, 'raw_bytes') or len(self.raw_bytes) < 0x48:
            return b'\x00' * 48
        
        # Extract the encrypted substruct area (48 bytes starting at offset 0x20)
        # This corresponds to the 'secure' union in the C code
        encrypted_data = self.raw_bytes[0x20:0x20 + 48]
        if len(encrypted_data) < 48:
            return b'\x00' * 48
        
        # Convert to 32-bit words for decryption (12 words total)
        encrypted_words = struct.unpack('<12I', encrypted_data)
        
        # Decrypt using the same algorithm as DecryptBoxMon in pokemon.c
        decrypted_words = []
        for word in encrypted_words:
            # First XOR with otId, then with personality (reverse of encryption)
            word ^= self.otId
            word ^= self.personality
            decrypted_words.append(word)
        
        return struct.pack('<12I', *decrypted_words)
    
    def get_substruct_order(self) -> List[int]:
        """
        Get the substruct order based on personality value.
        Returns list of 4 indices representing the order [0,1,2,3] should be read.
        Based on the SUBSTRUCT_CASE logic in pokemon.c
        """
        order_table = [
            [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2],
            [0, 2, 3, 1], [0, 3, 2, 1], [1, 0, 2, 3], [1, 0, 3, 2],
            [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
            [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2],
            [2, 3, 0, 1], [3, 2, 0, 1], [1, 2, 3, 0], [1, 3, 2, 0],
            [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0]
        ]
        return order_table[self.personality % 24]
    
    def get_substruct(self, substruct_type: int) -> Optional[bytes]:
        """
        Get the decrypted data for a specific substruct type (0-3).
        Returns 12 bytes of substruct data.
        """
        if not (0 <= substruct_type <= 3):
            return None
        
        decrypted_data = self.decrypt_substruct_data()
        if len(decrypted_data) < 48:
            return None
        
        # Get the actual position of this substruct type based on personality
        order = self.get_substruct_order()
        try:
            substruct_index = order.index(substruct_type)
        except ValueError:
            return None
        
        start_offset = substruct_index * 12
        return decrypted_data[start_offset:start_offset + 12]
    
    @property
    def moves_from_substruct(self) -> List[int]:
        """
        Extract moves from party Pokemon data.
        For party Pokemon, moves are stored in unencrypted area starting at offset 0x34.
        """
        if not hasattr(self, 'raw_bytes') or len(self.raw_bytes) < 0x3E:
            return [0, 0, 0, 0]
        
        try:
            # Moves are stored as 16-bit values in party Pokemon data (unencrypted)
            # at offsets 0x34, 0x36, 0x38, 0x3A
            moves = []
            for i in range(4):
                offset = 0x34 + (i * 2)
                if offset + 1 < len(self.raw_bytes):
                    move_id = struct.unpack('<H', self.raw_bytes[offset:offset+2])[0]
                    # Validate move ID range
                    if 0 <= move_id <= 1000:
                        moves.append(move_id)
                    else:
                        moves.append(0)
                else:
                    moves.append(0)
            return moves
        except (struct.error, IndexError):
            return [0, 0, 0, 0]
    
    @property
    def move_names(self) -> List[str]:
        """
        Get the move names for this Pokemon's current moves.
        """
        moves = self.moves_from_substruct
        names = []
        for move_id in moves:
            if move_id == 0:
                names.append("---")
            else:
                # Use the data loader for better move names
                move_name = get_move_name(move_id)
                names.append(move_name)
        return names


class SectorInfo(NamedTuple):
    id: int
    checksum: int
    counter: int
    valid: bool


class PokemonSaveParser:
    """
    Pokemon Quetzal rom hack save file parser
    
    This parser handles the specific save file format used by Pokemon Quetzal,
    which differs from standard pokeemerald-expansion in structure layout,
    and field sizes.
    """
    
    def __init__(self, save_path: str):
        self.save_path = Path(save_path)
        self.save_data: Optional[bytes] = None
        self.active_slot_start: int = 0
        self.sector_map: Dict[int, int] = {}

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
        footer_offset = (sector_index * SECTOR_SIZE) + SECTOR_SIZE - SECTOR_FOOTER_SIZE
        try:
            sector_id, checksum, signature, counter = struct.unpack(
                "<HHII",
                self.save_data[footer_offset:footer_offset + SECTOR_FOOTER_SIZE]
            )
            valid = signature == EMERALD_SIGNATURE
            return SectorInfo(sector_id, checksum, counter, valid)
        except (struct.error, IndexError):
            return SectorInfo(-1, 0, 0, False)

    def determine_active_slot(self) -> None:
        slot1_info = self.get_sector_info(0)
        slot2_info = self.get_sector_info(14)
        if slot2_info.counter > slot1_info.counter:
            self.active_slot_start = 14
        else:
            self.active_slot_start = 0

    def build_sector_map(self) -> None:
        self.sector_map = {}
        for i in range(14):
            sector_info = self.get_sector_info(self.active_slot_start + i)
            if sector_info.valid:
                self.sector_map[sector_info.id] = self.active_slot_start + i

    def extract_saveblock1(self) -> bytearray:
        if not self.save_data:
            raise ValueError("Save data not loaded")
        saveblock1_sectors = [i for i in range(1, 5) if i in self.sector_map]
        if not saveblock1_sectors:
            raise ValueError("No SaveBlock1 sectors found")
        if len(saveblock1_sectors) != 4:
            print(f"[INFO] Found {len(saveblock1_sectors)}/4 SaveBlock1 sectors (some data may be incomplete)")
        saveblock1_data = bytearray(SAVEBLOCK1_SIZE)
        for sector_id in saveblock1_sectors:
            sector_idx = self.sector_map[sector_id]
            start_offset = sector_idx * SECTOR_SIZE
            sector_data = self.save_data[start_offset:start_offset + SECTOR_DATA_SIZE]
            expected_chunk = sector_id - 1
            chunk_offset = expected_chunk * SECTOR_DATA_SIZE
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
            if pokemon_struct.species_id == 0:
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
            f"{'Slot':<5}"
            f"{'Dex ID':<8}"
            f"{'Nickname':<12}"
            f"{'Lv':<4}"
            f"{'Nature':<10}"
            f"{'HP':<30} "
            f"{'Atk':<5}"
            f"{'Def':<5}"
            f"{'Spe':<5}"
            f"{'SpA':<5}"
            f"{'SpD':<5}"
            f"{'OT Name':<10}"
            f"{'IDNo':<7}"
        )
        print(header)
        print("-" * len(header))
        for slot, pokemon in enumerate(party_pokemon, 1):
            hp_percent = (pokemon.effective_current_hp / pokemon.maxHp) if pokemon.maxHp > 0 else 0.0
            hp_bar_length = 20
            filled_bars = int(hp_bar_length * hp_percent)
            hp_bar = "█" * filled_bars + "░" * (hp_bar_length - filled_bars)
            hp_display = f"[{hp_bar}] {pokemon.effective_current_hp}/{pokemon.maxHp}"
            print(
                f"{slot:<5}"
                f"{pokemon.species_id:<8}"
                f"{pokemon.nickname_str:<12}"
                f"{pokemon.level:<4}"
                f"{pokemon.nature_str:<10}"
                f"{hp_display:<30} "
                f"{pokemon.attack:<5}"
                f"{pokemon.defense:<5}"
                f"{pokemon.speed:<5}"
                f"{pokemon.spAttack:<5}"
                f"{pokemon.spDefense:<5}"
                f"{pokemon.otName_str:<10}"
                f"{pokemon.otId_str:<7}"
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
            
            # Debug substruct data
            print(f"\nPersonality: 0x{pokemon.personality:08x}")
            print(f"OT ID: 0x{pokemon.otId:08x}")
            
            # Show decrypted substruct data
            decrypted_data = pokemon.decrypt_substruct_data()
            print(f"Decrypted substruct data ({len(decrypted_data)} bytes):")
            for i in range(0, len(decrypted_data), 12):
                substruct_chunk = decrypted_data[i:i+12]
                hex_str = ' '.join(f'{b:02x}' for b in substruct_chunk)
                print(f"  Substruct {i//12}: {hex_str}")
            
            # Show substruct order
            order = pokemon.get_substruct_order()
            print(f"Substruct order: {order}")
            
            # Show moves analysis
            moves = pokemon.moves_from_substruct
            print(f"Extracted moves: {moves}")

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


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

    parser = argparse.ArgumentParser(description='Pokemon Quetzal Rom Hack Save File Parser')
    parser.add_argument('save_file', nargs='?', default=DEFAULT_SAVE_PATH,
                        help='Path to the save file (default: ./save/player1.sav)')
    parser.add_argument('--debugParty', action='store_true', help='Display raw party pokemon bytes')
    parser.add_argument('--json', action='store_true', help='Return json instead of a human readable table')
    args = parser.parse_args()
    if args.save_file == DEFAULT_SAVE_PATH and len(sys.argv) == 1:
        print(f"[INFO] No save file specified, using default: {args.save_file}", file=sys.stderr)
    try:
        save_parser = PokemonSaveParser(args.save_file)
        save_data = save_parser.parse_save_file()
        if args.json:
            PokemonSaveParser.display_json_output(save_data)
        elif args.debugParty:
            PokemonSaveParser.display_party_pokemon_raw(save_data['party_pokemon'])
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