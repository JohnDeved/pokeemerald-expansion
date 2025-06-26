#!/usr/bin/env python3

import struct
import ctypes
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple, Any

# Save file structure constants
SECTOR_SIZE = 4096
SECTOR_DATA_SIZE = 3968
SECTOR_FOOTER_SIZE = 12
SAVEBLOCK1_SIZE = SECTOR_DATA_SIZE * 4
SAVEBLOCK2_SIZE = SECTOR_DATA_SIZE
EMERALD_SIGNATURE = 0x08012025

# Party Pokemon constants (for this save file format)
PARTY_START_OFFSET = 0x6B0
PARTY_POKEMON_SIZE = 104
MAX_PARTY_SIZE = 6

# Default paths and offsets
DEFAULT_SAVE_PATH = "./save/player1.sav"
PLAYER_NAME_OFFSET = 0x0

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
    0x79: "'", 0x7A: "'", 0x7B: """, 0x7C: """,
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


class SaveBlock2(ctypes.Structure):
    """Structure for SaveBlock2 data in Pokemon Emerald."""
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
    
    Pokemon Quetzal modifications from standard pokeemerald:
    - Nickname field is 18 bytes instead of 10 (Quetzal expansion)
    - Current HP is stored at offset 0x1B (different from standard)
    - Various field sizes and layouts modified for Quetzal's features
    - Experience, held items, and other fields may have different sizes/positions
    """
    _pack_ = 1
    _fields_ = [
        # BoxPokemon-like data (first 80 bytes) - but with differences from standard pokeemerald
        ("nickname", ctypes.c_uint8 * 18),      # 0x00 - Pokemon nickname (18 bytes in this format)
        ("unknown_12", ctypes.c_uint8 * 6),     # 0x12 - Language, flags, and other packed data
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
        ("unknown_5E", ctypes.c_uint8 * 10),    # 0x5E - Additional unknown data
    ]


class SectorInfo(NamedTuple):
    """Information about a save file sector."""
    id: int
    checksum: int
    counter: int
    valid: bool


class PokemonSaveParser:
    """
    Pokemon Quetzal rom hack save file parser with robust error handling.
    
    This parser handles the specific save file format used by Pokemon Quetzal,
    which differs from standard pokeemerald-expansion in structure layout,
    field sizes, and encryption. It can parse both intact and partially 
    corrupted save files.
    
    Pokemon Quetzal uses modified structures:
    - Extended nickname fields (18 bytes vs 10)
    - Different current HP storage location (0x1B)
    - Modified party Pokemon structure layout
    - Enhanced features requiring additional data fields
    
    Attributes:
        save_path: Path to the save file
        save_data: Raw save file bytes
        active_slot_start: Start offset of the active save slot
        sector_map: Mapping of sector IDs to their positions
        debug_mode: Whether to output debug information during parsing
    """
    
    def __init__(self, save_path: str):
        """Initialize the parser with a save file path."""
        self.save_path = Path(save_path)
        self.save_data: Optional[bytes] = None
        self.active_slot_start: int = 0
        self.sector_map: Dict[int, int] = {}
        self.debug_mode: bool = False

    def load_save_file(self) -> None:
        """Load the save file into memory."""
        if not self.save_path.exists():
            raise FileNotFoundError(f"Save file not found: {self.save_path}")
        try:
            with open(self.save_path, "rb") as f:
                self.save_data = f.read()
        except IOError as e:
            raise IOError(f"Failed to read save file: {e}")

    def decode_pokemon_string(self, encoded_bytes: bytes) -> str:
        """Decode a bytes object using the Pokémon character map."""
        result = ""
        for byte in encoded_bytes:
            if byte == 0xFF:  # Terminator
                break
            result += POKEMON_CHAR_MAP.get(byte, "?")
        return result

    @staticmethod
    def decode_pokemon_string_static(encoded_bytes: bytes) -> str:
        """Static version of decode_pokemon_string for use in display functions."""
        result = ""
        for byte in encoded_bytes:
            if byte == 0xFF:  # Terminator
                break
            result += POKEMON_CHAR_MAP.get(byte, "?")
        return result

    def get_sector_info(self, sector_index: int) -> SectorInfo:
        """Extract sector footer information for a given sector."""
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
        """Determine which save slot is active based on counter values."""
        slot1_info = self.get_sector_info(0)
        slot2_info = self.get_sector_info(14)
        print("[INFO] Detecting active save slot...")
        print(f"  Slot 1 (Sector 0): Counter = {slot1_info.counter}, Valid = {slot1_info.valid}")
        print(f"  Slot 2 (Sector 14): Counter = {slot2_info.counter}, Valid = {slot2_info.valid}")
        if slot2_info.counter > slot1_info.counter:
            self.active_slot_start = 14
            print("[INFO] Slot 2 is active (higher counter).")
        else:
            self.active_slot_start = 0
            print("[INFO] Slot 1 is active (higher or equal counter).")

    def build_sector_map(self) -> None:
        """Build a mapping of sector IDs to their positions."""
        self.sector_map = {}
        for i in range(14):
            sector_info = self.get_sector_info(self.active_slot_start + i)
            if sector_info.valid:
                self.sector_map[sector_info.id] = self.active_slot_start + i

    def extract_saveblock1(self) -> bytearray:
        """Extract and reconstruct SaveBlock1 data."""
        if not self.save_data:
            raise ValueError("Save data not loaded")
        saveblock1_sectors = [i for i in range(1, 5) if i in self.sector_map]
        if len(saveblock1_sectors) == 0:
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
        """Extract SaveBlock2 data."""
        if not self.save_data:
            raise ValueError("Save data not loaded")
        if 0 not in self.sector_map:
            raise ValueError("SaveBlock2 sector (ID 0) not found")
        sector_idx = self.sector_map[0]
        start_offset = sector_idx * SECTOR_SIZE
        saveblock2_data = self.save_data[start_offset:start_offset + SECTOR_DATA_SIZE]
        return saveblock2_data

    def parse_party_pokemon(self, saveblock1_data: bytes) -> List[PokemonData]:
        """
        Parse party Pokémon from SaveBlock1 data.
        
        This method uses the accurate PokemonData ctypes structure to extract
        Pokémon information from the save file format. The save file stores
        party Pokémon starting at offset 0x6B0, with each Pokémon data being
        104 bytes in size.
        
        Args:
            saveblock1_data: Raw SaveBlock1 data containing party information
            
        Returns:
            List of PokemonData objects with complete stats and metadata
        """
        party_pokemon = []
        for slot in range(MAX_PARTY_SIZE):
            pokemon_offset = PARTY_START_OFFSET + slot * PARTY_POKEMON_SIZE
            pokemon_data = saveblock1_data[pokemon_offset:pokemon_offset + PARTY_POKEMON_SIZE]
            if len(pokemon_data) < PARTY_POKEMON_SIZE:
                break
            if self.debug_mode:
                self._debug_pokemon_data(pokemon_data, slot + 1)
            if len(pokemon_data) < ctypes.sizeof(PokemonData):
                break
            pokemon_struct = PokemonData.from_buffer_copy(pokemon_data[:ctypes.sizeof(PokemonData)])
            if pokemon_struct.species_id == 0:
                break
            party_pokemon.append(pokemon_struct)
        return party_pokemon

    def parse_player_name(self, saveblock2_data: bytes) -> str:
        """Parse player name from SaveBlock2 data using ctypes structure."""
        if len(saveblock2_data) < ctypes.sizeof(SaveBlock2):
            raise ValueError("SaveBlock2 data too small")
        saveblock2 = SaveBlock2.from_buffer_copy(saveblock2_data)
        player_name_bytes = bytes(saveblock2.playerName)
        return self.decode_pokemon_string(player_name_bytes)

    def parse_play_time(self, saveblock2_data: bytes) -> Dict[str, int]:
        """Parse play time from SaveBlock2 data using ctypes structure."""
        if len(saveblock2_data) < ctypes.sizeof(SaveBlock2):
            raise ValueError("SaveBlock2 data too small")
        saveblock2 = SaveBlock2.from_buffer_copy(saveblock2_data)
        return {
            'hours': saveblock2.playTimeHours,
            'minutes': saveblock2.playTimeMinutes,
            'seconds': saveblock2.playTimeSeconds
        }

    SUBSTRUCT_ORDERS = [
        [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2], [0, 2, 3, 1], [0, 3, 2, 1],
        [1, 0, 2, 3], [1, 0, 3, 2], [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
        [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2], [2, 3, 0, 1], [3, 2, 0, 1],
        [1, 2, 3, 0], [1, 3, 2, 0], [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0]
    ]

    def parse_save_file(self) -> Dict[str, Any]:
        """Parse the entire save file and return structured data."""
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

    def _debug_pokemon_data(self, pokemon_data: bytes, slot: int) -> None:
        """Debug function to examine raw Pokemon data."""
        print(f"\n=== DEBUG: Pokemon Slot {slot} Raw Data ===")
        print("Offset: Data (hex)")
        for i in range(0, min(len(pokemon_data), 104), 16):
            hex_data = pokemon_data[i:i+16].hex(' ')
            print(f"0x{i:02X}: {hex_data}")
        if slot <= 6 and self.debug_mode:  # Show HP analysis for all Pokemon
            print(f"\n--- HP Analysis for Slot {slot} ---")
            max_hp_byte = pokemon_data[0x52] if len(pokemon_data) > 0x52 else 0
            current_hp_byte = pokemon_data[0x1B] if len(pokemon_data) > 0x1B else 0
            level_byte = pokemon_data[0x50] if len(pokemon_data) > 0x50 else 0
            print(f"Level: {level_byte}, Current HP: {current_hp_byte}/{max_hp_byte}")
            if current_hp_byte == 0:
                print("  Status: Fainted")
            elif current_hp_byte == max_hp_byte:
                print("  Status: Full Health")
            else:
                hp_percent = (current_hp_byte / max_hp_byte * 100) if max_hp_byte > 0 else 0
                print(f"  Status: {hp_percent:.1f}% Health")
            print(f"Stats: ATK:{pokemon_data[0x54]} DEF:{pokemon_data[0x56]} SPD:{pokemon_data[0x58]} SPA:{pokemon_data[0x5A]} SPD:{pokemon_data[0x5C]}")
        print("=" * 50)


class SaveFileDisplayer:
    """Handles display of parsed save file data."""
    
    @staticmethod
    def display_party_pokemon(party_pokemon: List[PokemonData]) -> None:
        """Display detailed party Pokémon information."""
        print("\n--- Party Pokémon Summary ---")
        if not party_pokemon:
            print("No Pokémon found in party.")
            return
        print(f"{'Slot':<4} {'Nickname':<12} {'Species ID':<12} {'Lv':<3} {'HP':<28} {'Stats (A/D/S/SA/SD)'}")
        print("-" * 95)
        for slot, pokemon in enumerate(party_pokemon, 1):
            nickname = PokemonSaveParser.decode_pokemon_string_static(bytes(pokemon.nickname))
            species_display = f"{pokemon.species_id}"
            hp_percent = (pokemon.currentHp / pokemon.maxHp) if pokemon.maxHp > 0 else 0
            hp_bar_length = 20
            filled_bars = int(hp_bar_length * hp_percent)
            hp_bar = "█" * filled_bars + "░" * (hp_bar_length - filled_bars)
            hp_display = f"[{hp_bar}] {pokemon.currentHp}/{pokemon.maxHp}"
            stats_display = f"{pokemon.attack}/{pokemon.defense}/{pokemon.speed}/{pokemon.spAttack}/{pokemon.spDefense}"
            print(f"{slot:<4} {nickname:<12} {species_display:<12} {pokemon.level:<3} {hp_display:<28} {stats_display}")

    @staticmethod
    def display_saveblock2_info(save_data: Dict[str, Any]) -> None:
        """Display SaveBlock2 information."""
        print("\n--- SaveBlock2 Data ---")
        print(f"Player Name: {save_data['player_name']}")
        play_time = save_data['play_time']
        if 'frames' in play_time:
            print(f"Play Time: {play_time['hours']}h {play_time['minutes']}m {play_time['seconds']}s {play_time['frames']}f")
        else:
            print(f"Play Time: {play_time['hours']}h {play_time['minutes']}m {play_time['seconds']}s")

    @staticmethod
    def display_save_info(save_data: Dict[str, Any]) -> None:
        """Display all parsed save file information."""
        print(f"Active save slot: {save_data['active_slot']}")
        print(f"Valid sectors found: {len(save_data['sector_map'])}")
        SaveFileDisplayer.display_party_pokemon(save_data['party_pokemon'])
        SaveFileDisplayer.display_saveblock2_info(save_data)


def main():
    """Main entry point for the script."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description='Pokemon Quetzal Rom Hack Save File Parser')
    parser.add_argument('save_file', nargs='?', default=DEFAULT_SAVE_PATH,
                        help='Path to the save file (default: ./save/player1.sav)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode to show raw Pokemon data')
    args = parser.parse_args()
    if args.save_file == DEFAULT_SAVE_PATH and len(sys.argv) == 1:
        print(f"[INFO] No save file specified, using default: {args.save_file}")
    try:
        save_parser = PokemonSaveParser(args.save_file)
        if args.debug:
            save_parser.debug_mode = True
        save_data = save_parser.parse_save_file()
        displayer = SaveFileDisplayer()
        displayer.display_save_info(save_data)
    except (FileNotFoundError, IOError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
