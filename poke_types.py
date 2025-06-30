import json
from typing import TypedDict, Any
from dataclasses import dataclass

# Data storage
_data: dict[str, dict[int, str]] = {}

# Type definitions for structured data
class PlayTimeData(TypedDict):
    hours: int
    minutes: int
    seconds: int

class PokemonDictData(TypedDict):
    personality: int
    otId: int
    nickname: str
    otName: str
    currentHp: int
    speciesId: int
    item: int
    move1: int
    move2: int
    move3: int
    move4: int
    pp1: int
    pp2: int
    pp3: int
    pp4: int
    hpEV: int
    atkEV: int
    defEV: int
    speEV: int
    spaEV: int
    spdEV: int
    ivData: int
    level: int
    maxHp: int
    attack: int
    defense: int
    speed: int
    spAttack: int
    spDefense: int
    displayOtId: str
    displayNature: str
    moves: list[int]
    moveNames: list[str]
    ppValues: list[int]
    evs: list[int]
    ivs: list[int]
    totalEvs: int
    totalIvs: int

class SaveData(TypedDict):
    party_pokemon: list[Any]  # Use Any to avoid circular import
    player_name: str
    play_time: PlayTimeData
    active_slot: int
    sector_map: dict[int, int]

@dataclass(frozen=True)
class PokemonStats:
    hp: int
    attack: int
    defense: int
    speed: int
    sp_attack: int
    sp_defense: int

@dataclass(frozen=True)
class MoveData:
    name: str
    id: int
    pp: int

@dataclass(frozen=True)
class PokemonMoves:
    move1: MoveData
    move2: MoveData
    move3: MoveData
    move4: MoveData
    
    @classmethod
    def from_raw_data(cls, move1_id: int, move2_id: int, move3_id: int, move4_id: int,
                      pp1: int, pp2: int, pp3: int, pp4: int) -> 'PokemonMoves':
        return cls(
            move1=MoveData(name=get_move_name(move1_id) if move1_id != 0 else "---", id=move1_id, pp=pp1),
            move2=MoveData(name=get_move_name(move2_id) if move2_id != 0 else "---", id=move2_id, pp=pp2),
            move3=MoveData(name=get_move_name(move3_id) if move3_id != 0 else "---", id=move3_id, pp=pp3),
            move4=MoveData(name=get_move_name(move4_id) if move4_id != 0 else "---", id=move4_id, pp=pp4)
        )
    
    def get_move_ids(self) -> list[int]:
        return [self.move1.id, self.move2.id, self.move3.id, self.move4.id]
    
    def get_move_names(self) -> list[str]:
        return [self.move1.name, self.move2.name, self.move3.name, self.move4.name]
    
    def get_pp_values(self) -> list[int]:
        return [self.move1.pp, self.move2.pp, self.move3.pp, self.move4.pp]
    
    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            'move1': {'name': self.move1.name, 'id': self.move1.id, 'pp': self.move1.pp},
            'move2': {'name': self.move2.name, 'id': self.move2.id, 'pp': self.move2.pp},
            'move3': {'name': self.move3.name, 'id': self.move3.id, 'pp': self.move3.pp},
            'move4': {'name': self.move4.name, 'id': self.move4.id, 'pp': self.move4.pp}
        }

@dataclass(frozen=True)
class PokemonEVs:
    hp: int
    attack: int
    defense: int
    speed: int
    sp_attack: int
    sp_defense: int
    
    def to_list(self) -> list[int]:
        return [self.hp, self.attack, self.defense, self.speed, self.sp_attack, self.sp_defense]
    
    @property
    def total(self) -> int:
        return sum(self.to_list())

@dataclass(frozen=True)
class PokemonIVs:
    hp: int
    attack: int
    defense: int
    speed: int
    sp_attack: int
    sp_defense: int
    
    def to_list(self) -> list[int]:
        return [self.hp, self.attack, self.defense, self.speed, self.sp_attack, self.sp_defense]
    
    @property
    def total(self) -> int:
        return sum(self.to_list())

def _load_data() -> None:
    files = {
        "pokemon_moves.json": "moves",
        "pokemon_species.json": "species", 
        "pokemon_charmap.json": "chars",
        "pokemon_natures.json": "natures"
    }
    
    for filename, key in files.items():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                _data[key] = {int(k): v for k, v in json.load(f).items()}
        except (FileNotFoundError, json.JSONDecodeError):
            _data[key] = {}

_load_data()

def get_move_name(move_id: int) -> str:
    return _data.get("moves", {}).get(move_id, f"Move {move_id}")

def get_species_name(species_id: int) -> str:
    return _data.get("species", {}).get(species_id, f"Species {species_id}")

def get_char_map() -> dict[int, str]:
    return _data.get("chars", {})

def get_nature_name(nature_id: int) -> str:
    return _data.get("natures", {}).get(nature_id, f"Nature {nature_id}")
