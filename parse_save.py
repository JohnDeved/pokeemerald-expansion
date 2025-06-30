#!/usr/bin/env python3

import struct
import ctypes
import argparse
import sys
import json
from pathlib import Path
from typing import Optional, NamedTuple, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

# Import type definitions and data loading functions
from poke_types import (
    PlayTimeData, PokemonDictData, SaveData, PokemonStats, MoveData, PokemonMoves,
    PokemonEVs, PokemonIVs, _data, get_move_name, get_species_name, get_char_map, get_nature_name
)

# Constants
SECTOR_SIZE = 4096
SECTOR_DATA_SIZE = 3968
SECTOR_FOOTER_SIZE = 12
SAVEBLOCK1_SIZE = SECTOR_DATA_SIZE * 4
EMERALD_SIGNATURE = 0x08012025
SECTORS_PER_SLOT = 18
TOTAL_SECTORS = 32
PARTY_START_OFFSET = 0x6A8
PARTY_POKEMON_SIZE = 104
MAX_PARTY_SIZE = 6
DEFAULT_SAVE_PATH = "./save/player1.sav"

# Data storage
_data: dict[str, dict[int, str]] = {}

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
    _pack_ = 1
    _fields_ = [
        ("personality", ctypes.c_uint32),
        ("otId", ctypes.c_uint32),
        ("nickname", ctypes.c_uint8 * 10),
        ("unknown_12", ctypes.c_uint8 * 2),
        ("otName", ctypes.c_uint8 * 7),
        ("unknown_1B", ctypes.c_uint8 * 8),
        ("currentHp", ctypes.c_uint16),
        ("unknown_25", ctypes.c_uint8 * 3),
        ("speciesId", ctypes.c_uint16),
        ("item", ctypes.c_uint16),
        ("unknown_2C", ctypes.c_uint8 * 8),
        ("move1", ctypes.c_uint16),
        ("move2", ctypes.c_uint16),
        ("move3", ctypes.c_uint16),
        ("move4", ctypes.c_uint16),
        ("pp1", ctypes.c_uint8),
        ("pp2", ctypes.c_uint8),
        ("pp3", ctypes.c_uint8),
        ("pp4", ctypes.c_uint8),
        ("hpEV", ctypes.c_uint8),
        ("atkEV", ctypes.c_uint8),
        ("defEV", ctypes.c_uint8),
        ("speEV", ctypes.c_uint8),
        ("spaEV", ctypes.c_uint8),
        ("spdEV", ctypes.c_uint8),
        ("unknown_46", ctypes.c_uint8 * 10),
        ("ivData", ctypes.c_uint32),
        ("unknown_54", ctypes.c_uint8 * 4),
        ("level", ctypes.c_uint8),
        ("unknown_59", ctypes.c_uint8),
        ("maxHp", ctypes.c_uint16),
        ("attack", ctypes.c_uint16),
        ("defense", ctypes.c_uint16),
        ("speed", ctypes.c_uint16),
        ("spAttack", ctypes.c_uint16),
        ("spDefense", ctypes.c_uint16),
        ("unknown_66", ctypes.c_uint8 * 2),
    ]
    
    raw_bytes: bytes
    
    @property
    def nature_str(self) -> str:
        return get_nature_name((self.personality & 0xFF) % 25)
    
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
    def moves_data(self) -> PokemonMoves:
        return PokemonMoves.from_raw_data(
            move1_id=self.move1, move2_id=self.move2, move3_id=self.move3, move4_id=self.move4,
            pp1=self.pp1, pp2=self.pp2, pp3=self.pp3, pp4=self.pp4
        )
    
    @property
    def evs(self) -> list[int]:
        return [self.hpEV, self.atkEV, self.defEV, self.speEV, self.spaEV, self.spdEV]
    
    @property
    def evs_structured(self) -> PokemonEVs:
        return PokemonEVs(
            hp=self.hpEV, attack=self.atkEV, defense=self.defEV,
            speed=self.speEV, sp_attack=self.spaEV, sp_defense=self.spdEV
        )
    
    @property
    def ivs(self) -> list[int]:
        iv = self.ivData
        return [(iv >> (i * 5)) & 0x1F for i in range(6)]
    
    @property
    def ivs_structured(self) -> PokemonIVs:
        ivs_list = self.ivs
        return PokemonIVs(
            hp=ivs_list[0], attack=ivs_list[1], defense=ivs_list[2],
            speed=ivs_list[3], sp_attack=ivs_list[4], sp_defense=ivs_list[5]
        )
    
    @property
    def stats_structured(self) -> PokemonStats:
        return PokemonStats(
            hp=self.maxHp, attack=self.attack, defense=self.defense,
            speed=self.speed, sp_attack=self.spAttack, sp_defense=self.spDefense
        )


class SectorInfo(NamedTuple):
    id: int
    checksum: int
    counter: int
    valid: bool


class PokemonSaveParser:
    
    def __init__(self, save_path: str, forced_slot: Optional[int] = None) -> None:
        self.save_path = Path(save_path)
        self.save_data: Optional[bytes] = None
        self.active_slot_start: int = 0
        self.sector_map: dict[int, int] = {}
        self.forced_slot = forced_slot

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
            if byte == 0xFF:
                break
            result += char_map.get(byte, "?")
        return result

    def get_sector_info(self, sector_index: int) -> SectorInfo:
        if not self.save_data:
            raise ValueError("Save data not loaded")
        
        footer_offset = (sector_index * SECTOR_SIZE) + SECTOR_SIZE - SECTOR_FOOTER_SIZE
        
        if footer_offset + SECTOR_FOOTER_SIZE > len(self.save_data):
            return SectorInfo(-1, 0, 0, False)
            
        try:
            sector_id, checksum, signature, counter = struct.unpack(
                "<HHII",
                self.save_data[footer_offset:footer_offset + SECTOR_FOOTER_SIZE]
            )
            
            if signature != EMERALD_SIGNATURE:
                return SectorInfo(sector_id, checksum, counter, False)
            
            sector_start = sector_index * SECTOR_SIZE
            sector_data = self.save_data[sector_start:sector_start + SECTOR_DATA_SIZE]
            
            calculated_checksum = self.calculate_sector_checksum(sector_data)
            valid = (calculated_checksum == checksum)
            
            return SectorInfo(sector_id, checksum, counter, valid)
        except (struct.error, IndexError):
            return SectorInfo(-1, 0, 0, False)

    def determine_active_slot(self) -> None:
        if self.forced_slot is not None:
            self.active_slot_start = 0 if self.forced_slot == 1 else 14
            return
        
        slot1_counter = max((self.get_sector_info(i).counter for i in range(18) 
                            if self.get_sector_info(i).valid), default=0)
        slot2_counter = max((self.get_sector_info(i).counter for i in range(14, 32) 
                            if self.get_sector_info(i).valid), default=0)
        
        self.active_slot_start = 14 if slot2_counter >= slot1_counter else 0

    def debug_save_slots(self) -> None:
        print("\n--- Save Slot Debug Information ---")
        
        def analyze_slot(slot_range: range, slot_name: str) -> tuple[int, int]:
            valid_sectors: list[int] = []
            counters: list[int] = []
            for i in slot_range:
                sector_info = self.get_sector_info(i)
                if sector_info.valid:
                    valid_sectors.append(i)
                    counters.append(sector_info.counter)
                    print(f"  Sector {i}: ID={sector_info.id}, Counter={sector_info.counter:08X}")
            
            max_counter = max(counters) if counters else 0
            print(f"{slot_name}: {len(valid_sectors)} valid sectors, max counter {max_counter:08X}")
            return len(valid_sectors), max_counter
        
        _, slot1_counter = analyze_slot(range(18), "Slot 1 (sectors 0-17)")
        _, slot2_counter = analyze_slot(range(14, 32), "Slot 2 (sectors 14-31)")
        
        active_slot = 14 if slot2_counter >= slot1_counter else 0
        print(f"\nActive slot: {active_slot} (highest counter wins, slot 2 wins ties)")

    def build_sector_map(self) -> None:
        self.sector_map = {}
        
        if self.forced_slot is not None:
            sector_range = range(18) if self.forced_slot == 1 else range(14, 32)
        else:
            sector_range = range(self.active_slot_start, self.active_slot_start + 18)
        
        for i in sector_range:
            sector_info = self.get_sector_info(i)
            if sector_info.valid:
                self.sector_map[sector_info.id] = i

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

    def parse_party_pokemon(self, saveblock1_data: bytes) -> list[PokemonData]:
        party_pokemon = []
        for slot in range(MAX_PARTY_SIZE):
            offset = PARTY_START_OFFSET + slot * PARTY_POKEMON_SIZE
            data = saveblock1_data[offset:offset + PARTY_POKEMON_SIZE]
            
            if len(data) < ctypes.sizeof(PokemonData):
                break
                
            pokemon = PokemonData.from_buffer_copy(data[:ctypes.sizeof(PokemonData)])
            if pokemon.speciesId == 0:
                break
                
            pokemon.raw_bytes = data
            party_pokemon.append(pokemon)
        return party_pokemon

    def parse_player_name(self, saveblock2_data: bytes) -> str:
        saveblock2 = SaveBlock2.from_buffer_copy(saveblock2_data)
        return PokemonSaveParser.decode_pokemon_string(bytes(saveblock2.playerName))

    def parse_play_time(self, saveblock2_data: bytes) -> PlayTimeData:
        saveblock2 = SaveBlock2.from_buffer_copy(saveblock2_data)
        return PlayTimeData(
            hours=saveblock2.playTimeHours,
            minutes=saveblock2.playTimeMinutes,
            seconds=saveblock2.playTimeSeconds
        )

    def parse_save_file(self) -> SaveData:
        self.load_save_file()
        self.determine_active_slot()
        self.build_sector_map()
        saveblock1_data = self.extract_saveblock1()
        saveblock2_data = self.extract_saveblock2()
        player_name = self.parse_player_name(saveblock2_data)
        party_pokemon = self.parse_party_pokemon(saveblock1_data)
        play_time = self.parse_play_time(saveblock2_data)
        return SaveData(
            party_pokemon=party_pokemon,
            player_name=player_name,
            play_time=play_time,
            active_slot=self.active_slot_start,
            sector_map=self.sector_map
        )

    @staticmethod
    def display_party_pokemon(party_pokemon: list[PokemonData]) -> None:
        print("\n--- Party Pokémon Summary ---")
        if not party_pokemon:
            print("No Pokémon found in party.")
            return
        
        header = f"{'Slot':<5}{'Dex ID':<8}{'Nickname':<12}{'Lv':<4}{'Nature':<10}{'HP':<30} {'Atk':<5}{'Def':<5}{'Spe':<5}{'SpA':<5}{'SpD':<5}{'OT Name':<10}{'IDNo':<7}"
        print(header)
        print("-" * len(header))
        
        for slot, pokemon in enumerate(party_pokemon, 1):
            hp_bars = int(20 * pokemon.currentHp / pokemon.maxHp) if pokemon.maxHp > 0 else 0
            hp_display = f"[{'█' * hp_bars}{'░' * (20 - hp_bars)}] {pokemon.currentHp}/{pokemon.maxHp}"
            
            print(f"{slot:<5}{pokemon.speciesId:<8}{pokemon.nickname_str:<12}{pokemon.level:<4}"
                  f"{pokemon.nature_str:<10}{hp_display:<30} {pokemon.attack:<5}{pokemon.defense:<5}"
                  f"{pokemon.speed:<5}{pokemon.spAttack:<5}{pokemon.spDefense:<5}"
                  f"{pokemon.otName_str:<10}{pokemon.otId_str:<7}")

    @staticmethod
    def display_saveblock2_info(save_data: SaveData) -> None:
        print("\n--- SaveBlock2 Data ---")
        print(f"Player Name: {save_data['player_name']}")
        play_time = save_data['play_time']
        print(f"Play Time: {play_time['hours']}h {play_time['minutes']}m {play_time['seconds']}s")

    @staticmethod
    def display_save_info(save_data: SaveData) -> None:
        print(f"Active save slot: {save_data['active_slot']}")
        print(f"Valid sectors found: {len(save_data['sector_map'])}")
        PokemonSaveParser.display_party_pokemon(save_data['party_pokemon'])
        PokemonSaveParser.display_saveblock2_info(save_data)

    @staticmethod
    def display_party_pokemon_raw(party_pokemon: list[PokemonData]) -> None:
        print("\n--- Party Pokémon Raw Bytes ---")
        if not party_pokemon:
            print("No Pokémon found in party.")
            return
        for slot, pokemon in enumerate(party_pokemon, 1):
            print(f"\n--- Slot {slot}: {pokemon.nickname_str} ---")
            print(' '.join(f'{b:02x}' for b in pokemon.raw_bytes))

    @staticmethod
    def pokemon_to_dict(pokemon: PokemonData) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for field_info in pokemon._fields_:
            field_name = field_info[0]
            value = getattr(pokemon, field_name)
            if field_name in ["nickname", "otName"]:
                data[field_name] = PokemonSaveParser.decode_pokemon_string(bytes(value))
            elif isinstance(value, ctypes.Array):
                data[field_name] = list(value)  # type: ignore
            else:
                data[field_name] = int(value) if hasattr(value, '__int__') else value
                
        data.update({
            'displayOtId': pokemon.otId_str,
            'displayNature': pokemon.nature_str,
            'moves': pokemon.moves_data.to_dict(),
            'evs': pokemon.evs,
            'ivs': pokemon.ivs,
            'totalEvs': sum(pokemon.evs),
            'totalIvs': sum(pokemon.ivs)
        })
        return data

    @staticmethod
    def display_json_output(save_data: SaveData) -> None:
        party_data = [PokemonSaveParser.pokemon_to_dict(p) for p in save_data['party_pokemon']]
        output = {
            'player_name': save_data['player_name'],
            'play_time': save_data['play_time'],
            'active_slot': save_data['active_slot'],
            'sector_map': save_data['sector_map'],
            'party_pokemon': party_data
        }
        print(json.dumps(output))

    @staticmethod
    def _create_basic_info_table(pokemon: PokemonData) -> Table:
        info_table = Table(show_header=False, box=box.SIMPLE, pad_edge=False)
        info_table.add_column("Field", style="cyan", width=12)
        info_table.add_column("Value", style="white")
        
        hp_bar = "█" * (pokemon.currentHp * 15 // pokemon.maxHp) if pokemon.maxHp > 0 else ""
        
        info_table.add_row("Species", f"[bold]{pokemon.species_name}[/bold] (#{pokemon.speciesId})")
        info_table.add_row("Nickname", f"[yellow]{pokemon.nickname_str}[/yellow]")
        info_table.add_row("Level", f"[bright_white]{pokemon.level}[/bright_white]")
        info_table.add_row("Nature", f"[magenta]{pokemon.nature_str}[/magenta]")
        info_table.add_row("Trainer", f"{pokemon.otName_str} ([dim]{pokemon.otId_str}[/dim])")
        info_table.add_row("HP", f"[blue]{hp_bar}[/blue] {pokemon.currentHp}/{pokemon.maxHp}")
        return info_table

    @staticmethod
    def _create_stats_table(pokemon: PokemonData) -> Table:
        stats_table = Table(title="[cyan]Base Stats[/cyan]", box=box.ROUNDED, width=35)
        stats_table.add_column("Stat", style="cyan", width=8)
        stats_table.add_column("Value", justify="right", style="yellow", width=6)
        stats_table.add_column("EV", justify="right", style="green", width=4)
        stats_table.add_column("IV", justify="right", style="bright_blue", width=4)
        
        evs = pokemon.evs
        ivs = pokemon.ivs
        stats_table.add_row("HP", f"{pokemon.maxHp}", f"{evs[0]}", f"{ivs[0]}")
        stats_table.add_row("Attack", f"{pokemon.attack}", f"{evs[1]}", f"{ivs[1]}")
        stats_table.add_row("Defense", f"{pokemon.defense}", f"{evs[2]}", f"{ivs[2]}")
        stats_table.add_row("Speed", f"{pokemon.speed}", f"{evs[3]}", f"{ivs[3]}")
        stats_table.add_row("Sp.Atk", f"{pokemon.spAttack}", f"{evs[4]}", f"{ivs[4]}")
        stats_table.add_row("Sp.Def", f"{pokemon.spDefense}", f"{evs[5]}", f"{ivs[5]}")
        return stats_table

    @staticmethod
    def _create_moves_table(pokemon: PokemonData) -> Table:
        moves_table = Table(title="[green]Moves[/green]", box=box.ROUNDED, width=45)
        moves_table.add_column("#", width=2)
        moves_table.add_column("Move", style="green")
        moves_table.add_column("PP", justify="center", style="yellow", width=4)
        
        for i, (move_name, pp) in enumerate(zip(pokemon.moves_data.get_move_names(), pokemon.moves_data.get_pp_values()), 1):
            if move_name != "---":
                moves_table.add_row(f"{i}", move_name, f"{pp}")
            else:
                moves_table.add_row(f"{i}", "[dim]---[/dim]", "[dim]---[/dim]")
        return moves_table

    @staticmethod
    def _create_summary_table(pokemon: PokemonData) -> Table:
        evs = pokemon.evs
        ivs = pokemon.ivs
        ev_total = sum(evs)
        iv_total = sum(ivs)
        ev_color = "green" if ev_total <= 510 else "red"
        iv_color = "bright_green" if iv_total >= 155 else "yellow" if iv_total >= 93 else "red"
        
        summary_table = Table(show_header=False, box=box.SIMPLE, pad_edge=False)
        summary_table.add_column("Label", style="cyan", width=12)
        summary_table.add_column("Value", style="white")
        summary_table.add_row("Total EVs", f"[{ev_color}]{ev_total}[/{ev_color}]/510")
        summary_table.add_row("Total IVs", f"[{iv_color}]{iv_total}[/{iv_color}]/186")
        return summary_table

    @staticmethod
    def display_party_pokemon_detailed(party_pokemon: list[PokemonData]) -> None:
        console = Console()
        
        if not party_pokemon:
            console.print(Panel("No Pokémon found in party.", title="Party", style="red"))
            return
        
        console.print(Panel.fit("🎮 POKÉMON PARTY SUMMARY 🎮", style="bold magenta"))
        
        for slot, pokemon in enumerate(party_pokemon, 1):
            info_table = PokemonSaveParser._create_basic_info_table(pokemon)
            stats_table = PokemonSaveParser._create_stats_table(pokemon)
            moves_table = PokemonSaveParser._create_moves_table(pokemon)
            summary_table = PokemonSaveParser._create_summary_table(pokemon)
            
            left_panel = Panel(info_table, title="[bold]Basic Info[/bold]", border_style="blue")
            right_content = Table.grid()
            right_content.add_row(stats_table)
            right_content.add_row("")
            right_content.add_row(moves_table)
            right_content.add_row("")
            right_content.add_row(summary_table)
            
            layout = Columns([left_panel, right_content], equal=False, expand=True)
            pokemon_panel = Panel(
                layout,
                title=f"[bold]Slot {slot}: {pokemon.nickname_str.upper()}[/bold]",
                border_style="bright_blue",
                padding=(1, 2)
            )
            
            console.print(pokemon_panel)
            console.print()

    def calculate_sector_checksum(self, sector_data: bytes) -> int:
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

    parser = argparse.ArgumentParser(description='Pokemon Quetzal save file parser')
    parser.add_argument('save_file', nargs='?', default=DEFAULT_SAVE_PATH, help='Path to save file')
    parser.add_argument('--debugParty', action='store_true', help='Show raw Pokemon bytes')
    parser.add_argument('--debugSlots', action='store_true', help='Show slot debug info')
    parser.add_argument('--detailed', action='store_true', help='Show detailed Pokemon info')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    slot_group = parser.add_mutually_exclusive_group()
    slot_group.add_argument('--slot1', action='store_true', help='Force slot 1')
    slot_group.add_argument('--slot2', action='store_true', help='Force slot 2')
    
    args = parser.parse_args()
    
    forced_slot = 1 if args.slot1 else 2 if args.slot2 else None
    
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
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()