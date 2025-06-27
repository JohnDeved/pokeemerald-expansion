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

# Pokémon character encoding map
POKEMON_CHAR_MAP = {
    0x00: " ", 0x01: "À", 0x02: "Á", 0x03: "Â", 0x04: "Ç", 0x05: "È", 0x06: "É", 0x07: "Ê",
    0x08: "Ë", 0x09: "Ì", 0x0B: "Î", 0x0C: "Ï", 0x0D: "Ò", 0x0E: "Ó", 0x0F: "Ô",
    0x10: "Œ", 0x11: "Ù", 0x12: "Ú", 0x13: "Û", 0x14: "Ñ", 0x15: "ß", 0x16: "à", 0x17: "á",
    0x19: "ç", 0x1A: "è", 0x1B: "é", 0x1C: "ê", 0x1D: "ë", 0x1E: "ì", 0x20: "î",
    0x21: "ï", 0x22: "ò", 0x23: "ó", 0x24: "ô", 0x25: "œ", 0x26: "ù", 0x27: "ú", 0x28: "û",
    0x29: "ñ", 0x2A: "º", 0x2B: "ª", 0x2D: "&", 0x2E: "+", 0x34: "[", 0x35: "]",
    0x51: "poke", 0x52: "POKE", 0x53: "block", 0x54: "BLOCK",
    0x5A: "Í", 0x5B: "%", 0x5C: "(", 0x5D: ")",
    0x79: "'", 0x7A: "'", 0x7B: "\"", 0x7C: "\"",
    0x85: "<...>", 0xA1: "0", 0xA2: "1", 0xA3: "2", 0xA4: "3", 0xA5: "4",
    0xA6: "5", 0xA7: "6", 0xA8: "7", 0xA9: "8", 0xAA: "9",
    0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-", 0xAF: "·", 0xB0: "...", 0xB1: "«", 0xB2: "»",
    0xB3: "'", 0xB4: "'", 0xB5: "♂", 0xB6: "♀", 0xB7: "money", 0xB8: ",", 0xB9: "x", 0xBA: "/",
    0xBB: "A", 0xBC: "B", 0xBD: "C", 0xBE: "D", 0xBF: "E", 0xC0: "F", 0xC1: "G", 0xC2: "H", 0xC3: "I",
    0xC4: "J", 0xC5: "K", 0xC6: "L", 0xC7: "M", 0xC8: "N", 0xC9: "O", 0xCA: "P", 0xCB: "Q", 0xCC: "R",
    0xCD: "S", 0xCE: "T", 0xCF: "U", 0xD0: "V", 0xD1: "W", 0xD2: "X", 0xD3: "Y", 0xD4: "Z",
    0xD5: "a", 0xD6: "b", 0xD7: "c", 0xD8: "d", 0xD9: "e", 0xDA: "f", 0xDB: "g", 0xDC: "h", 0xDD: "i",
    0xDE: "j", 0xDF: "k", 0xE0: "l", 0xE1: "m", 0xE2: "n", 0xE3: "o", 0xE4: "p", 0xE5: "q", 0xE6: "r",
    0xE7: "s", 0xE8: "t", 0xE9: "u", 0xEA: "v", 0xEB: "w", 0xEC: "x", 0xED: "y", 0xEE: "z",
    0xFF: " "
}

# Pokémon nature map
POKEMON_NATURE_MAP = {
    0: "Hardy",
    1: "Lonely",
    2: "Brave",
    3: "Adamant",
    4: "Naughty",
    5: "Bold",
    6: "Docile",
    7: "Relaxed",
    8: "Impish",
    9: "Lax",
    10: "Timid",
    11: "Hasty",
    12: "Serious",
    13: "Jolly",
    14: "Naive",
    15: "Modest",
    16: "Mild",
    17: "Quiet",
    18: "Bashful",
    19: "Rash",
    20: "Calm",
    21: "Gentle",
    22: "Sassy",
    23: "Careful",
    24: "Quirky"
}


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
    """
    Pokemon data structure for Pokemon Quetzal rom hack (104 bytes total).
    
    This structure represents both the box data (80 bytes) and party data (24 bytes).
    Current HP verified at offset 0x1B through user testing.
    Stats (attack, defense, speed, sp.atk, sp.def, max HP) are 16-bit integers.
    There are most likely additional fields added for Quetzal's extended features.
    """
    _pack_ = 1
    _fields_ = [
        # BoxPokemon-like data (first 80 bytes) - but with differences from standard pokeemerald
        # ("personality", ctypes.c_uint32),  # 0x00 - Personality value (32-bit)
        ("nature", ctypes.c_uint8),  # 0x00 - Personality value (32-bit)
        ("shinyType", ctypes.c_uint8),  # 0x01 - Shiny type (0 = normal, 1 = shiny, 2 = alternate shiny
        ("unknown_02", ctypes.c_uint8),  # 0x02 - Unknown data (2 bytes
        ("unknown_04", ctypes.c_uint8),  # 0x04 - Unknown data (4 bytes, possibly flags or additional info)
        ("otId", ctypes.c_uint32),          # 0x00 - Original Trainer ID (32-bit)
        ("nickname", ctypes.c_uint8 * VANILLA_POKEMON_NAME_LENGTH),      # 0x00 - Pokemon nickname (18 bytes in this format)
        ("unknown_0A", ctypes.c_uint8 * 2),     # 0x0A - Unknown data (2 bytes)
        ("otName", ctypes.c_uint8 * PLAYER_NAME_LENGTH),      # 0x0C - Original Trainer name (7 bytes)
        ("unknown_12", ctypes.c_uint8 * 5),     # 0x12 - Language, flags, and other packed data
        ("unknown_18", ctypes.c_uint8 * 3),     # 0x18 - Unknown data
        ("currentHp", ctypes.c_uint8),          # 0x1B - Current HP ✓ VERIFIED
        ("unknown_1C", ctypes.c_uint8 * 4),     # 0x1C - Unknown data
        ("species_id", ctypes.c_uint16),        # 0x20 - Species ID (unencrypted, 16-bit)
        ("heldItem", ctypes.c_uint16),          # 0x22 - Held item ID (16-bit)
        ("unknown_24", ctypes.c_uint8 * 44),    # 0x24 - Encrypted Pokemon data (moves, IVs, etc.)
                                                # Note: Quetzal may have additional features stored here
                                                # such as extended movesets, new abilities, forms, etc.
                                                # This contains 4 substructures of 12 bytes each:
                                                # - Substruct0: Species, item, experience, friendship
                                                # - Substruct1: Moves and PP
                                                # - Substruct2: EVs and Contest stats (6 EVs + 6 contest)
                                                # - Substruct3: IVs, ribbons, and other flags
        
        # Party-specific data (24 bytes) - starts at offset 0x50
        ("level", ctypes.c_uint8),              # 0x50 - Pokemon level
        ("status", ctypes.c_uint8),             # 0x51 - Status condition
        ("maxHp", ctypes.c_uint16),             # 0x52 - Maximum HP (16-bit)
        ("attack", ctypes.c_uint16),            # 0x54 - Attack stat (16-bit)
        ("defense", ctypes.c_uint16),           # 0x56 - Defense stat (16-bit)
        ("speed", ctypes.c_uint16),             # 0x58 - Speed stat (16-bit)
        ("spAttack", ctypes.c_uint16),          # 0x5A - Special Attack stat (16-bit)
        ("spDefense", ctypes.c_uint16),         # 0x5C - Special Defense stat (16-bit)
    ]
    @property
    def displayNature(self) -> str:
        # The nature field may be out of range, so mod by 25
        index = self.nature % 25
        return POKEMON_NATURE_MAP.get(index, f"Unknown({self.nature})")
    @property
    def displayOtId(self) -> str:
        # Returns the lower 16 bits of otId as a zero-padded 5-digit string
        return f"{self.otId & 0xFFFF:05}"


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
        for byte in encoded_bytes:
            if byte == 0xFF:  # Terminator
                break
            result += POKEMON_CHAR_MAP.get(byte, "?")
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
        party_pokemon = self.parse_party_pokemon(saveblock1_data)
        player_name = self.parse_player_name(saveblock2_data)
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
        header = f" {'Slot':<5}{'Nature':<12}{'Nickname':<12}{'OT Name':<10}{'IDNo':<7}{'Dex ID':<8}{'Lv':<4}{'HP':<30} {'Atk':<5}{'Def':<5}{'Spe':<5}{'SpA':<5}{'SpD':<5}"
        print(header)
        print("-" * len(header))
        for slot, pokemon in enumerate(party_pokemon, 1):
            nickname = PokemonSaveParser.decode_pokemon_string(bytes(pokemon.nickname))
            ot_name = PokemonSaveParser.decode_pokemon_string(bytes(pokemon.otName))
            species_display = f"{pokemon.species_id}"
            hp_percent = (pokemon.currentHp / pokemon.maxHp) if pokemon.maxHp > 0 else 0.0
            hp_bar_length = 20
            filled_bars = int(hp_bar_length * hp_percent)
            hp_bar = "█" * filled_bars + "░" * (hp_bar_length - filled_bars)
            hp_text = f"{pokemon.currentHp}/{pokemon.maxHp}"
            hp_display = f"[{hp_bar}] {hp_text}"
            stats_line = f"{pokemon.attack:<5}{pokemon.defense:<5}{pokemon.speed:<5}{pokemon.spAttack:<5}{pokemon.spDefense:<5}"
            print(f" {slot:<5}{pokemon.displayNature:<12}{nickname:<12}{ot_name:<10}{pokemon.displayOtId:<7}{species_display:<8}{pokemon.level:<4}{hp_display:<30} {stats_line}")

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
            raw_bytes = pokemon.raw_bytes
            print(' '.join(f'{b:02x}' for b in raw_bytes))

    @staticmethod
    def pokemon_to_dict(pokemon: PokemonData) -> Dict[str, Any]:
        data = {}
        for field_name, _ in pokemon._fields_:
            value = getattr(pokemon, field_name)
            if field_name in ["nickname", "otName"]:
                data[field_name] = PokemonSaveParser.decode_pokemon_string(bytes(value))
            elif isinstance(value, ctypes.Array):
                data[field_name] = list(value)
            else:
                data[field_name] = value
        data['displayOtId'] = pokemon.displayOtId
        data['displayNature'] = pokemon.displayNature
        return data

    @staticmethod
    def display_json_output(save_data: Dict[str, Any]) -> None:
        party_pokemon_for_json = [PokemonSaveParser.pokemon_to_dict(p) for p in save_data['party_pokemon']]

        json_output = {
            'player_name': save_data['player_name'],
            'play_time': save_data['play_time'],
            'active_slot': save_data['active_slot'],
            'sector_map': save_data['sector_map'],
            'party_pokemon': party_pokemon_for_json
        }
        print(json.dumps(json_output))


def main():
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