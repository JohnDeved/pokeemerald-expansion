#!/usr/bin/env python3
"""
Pokemon Data Parser for pokeemerald-expansion
Extracts moves, species, and other data from C header files
"""

import re
import json
from pathlib import Path
from typing import Dict, List

class PokemonDataParser:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.moves_data: Dict[int, str] = {}
        self.species_data: Dict[int, str] = {}
        self.char_map_data: Dict[int, str] = {}
        self.natures_data: Dict[int, str] = {}
        
    def parse_moves(self) -> Dict[int, str]:
        """Parse moves from constants/moves.h"""
        moves_file = self.project_root / "include/constants/moves.h"
        moves_map = {}
        
        if not moves_file.exists():
            print(f"Warning: {moves_file} not found")
            return moves_map
            
        with open(moves_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Pattern to match: #define MOVE_NAME number
        pattern = r'#define\s+MOVE_(\w+)\s+(\d+)'
        matches = re.findall(pattern, content)
        
        for move_name, move_id in matches:
            # Convert MOVE_NAME to "Move Name"
            formatted_name = move_name.replace('_', ' ').title()
            # Handle special cases
            formatted_name = formatted_name.replace('Hp', 'HP')
            formatted_name = formatted_name.replace('Pp', 'PP')
            formatted_name = formatted_name.replace('U Turn', 'U-turn')
            formatted_name = formatted_name.replace('V Create', 'V-create')
            
            moves_map[int(move_id)] = formatted_name
            
        self.moves_data = moves_map
        return moves_map
    
    def parse_species(self) -> Dict[int, str]:
        """Parse species from constants/species.h"""
        species_file = self.project_root / "include/constants/species.h"
        species_map = {}
        
        if not species_file.exists():
            print(f"Warning: {species_file} not found")
            return species_map
            
        with open(species_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Pattern to match: #define SPECIES_NAME number
        pattern = r'#define\s+SPECIES_(\w+)\s+(\d+)'
        matches = re.findall(pattern, content)
        
        for species_name, species_id in matches:
            if species_name == "NONE":
                continue
                
            # Convert SPECIES_NAME to "Species Name"
            formatted_name = species_name.replace('_', ' ').title()
            # Handle special cases
            formatted_name = formatted_name.replace(' F', '♀')  # Female symbol
            formatted_name = formatted_name.replace(' M', '♂')  # Male symbol
            formatted_name = formatted_name.replace('Ho Oh', 'Ho-Oh')
            formatted_name = formatted_name.replace('Mime Jr', 'Mime Jr.')
            
            species_map[int(species_id)] = formatted_name
            
        self.species_data = species_map
        return species_map
    
    def parse_char_map(self) -> Dict[int, str]:
        """Parse character map from charmap.txt"""
        charmap_file = self.project_root / "charmap.txt"
        char_map = {}
        
        if not charmap_file.exists():
            print(f"Warning: {charmap_file} not found")
            return char_map
            
        try:
            with open(charmap_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('//') or '=' not in line:
                        continue
                    
                    # Parse lines like: 'A' = BB or PKMN = 53 54
                    parts = line.split('=', 1)
                    if len(parts) != 2:
                        continue
                    
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # Handle quoted characters like 'A' = BB
                    if left.startswith("'") and left.endswith("'") and len(left) >= 3:
                        char = left[1:-1]  # Extract character from quotes
                        # Handle hex values (can be space-separated for multi-byte)
                        hex_values = right.split()
                        if hex_values:
                            try:
                                # Use first hex value for the character mapping
                                hex_val = int(hex_values[0], 16)
                                char_map[hex_val] = char
                            except ValueError:
                                continue
                    
                    # Handle special cases like PKMN, POKEBLOCK etc.
                    elif not left.startswith("'"):
                        # For now, just handle simple single-byte mappings
                        hex_values = right.split()
                        if len(hex_values) == 1:
                            try:
                                hex_val = int(hex_values[0], 16)
                                # Map special tokens to readable strings
                                if left == "PK":
                                    char_map[hex_val] = "poke"
                                elif left == "PKMN":
                                    char_map[hex_val] = "POKE" 
                                elif left == "LV":
                                    char_map[hex_val] = "["
                                elif left == "NBSP":
                                    char_map[hex_val] = " "
                                # Add more special mappings as needed
                            except ValueError:
                                continue
            
            # Add terminator and fallback mappings
            char_map[0xFF] = " "  # Common terminator
            
        except Exception as e:
            print(f"Warning: Could not parse charmap.txt: {e}")
            # Fallback to minimal character map
            char_map = {
                0x00: " ", 0xFF: " ",
                0xBB: "A", 0xBC: "B", 0xBD: "C", 0xBE: "D", 0xBF: "E",
                0xA1: "0", 0xA2: "1", 0xA3: "2", 0xA4: "3", 0xA5: "4"
            }
        
        self.char_map_data = char_map
        return char_map
    
    def parse_natures(self) -> Dict[int, str]:
        """Parse natures - using standard Pokemon nature order"""
        natures_map = {
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
        
        self.natures_data = natures_map
        return natures_map

    def get_move_name(self, move_id: int) -> str:
        """Get move name by ID"""
        if not self.moves_data:
            self.parse_moves()
        return self.moves_data.get(move_id, f"Move {move_id}")
    
    def get_species_name(self, species_id: int) -> str:
        """Get species name by ID"""
        if not self.species_data:
            self.parse_species()
        return self.species_data.get(species_id, f"Species {species_id}")
    
    def get_char_map(self, char_code: int) -> str:
        """Get character by code"""
        if not self.char_map_data:
            self.parse_char_map()
        return self.char_map_data.get(char_code, "?")
    
    def get_nature_name(self, nature_id: int) -> str:
        """Get nature name by ID"""
        if not self.natures_data:
            self.parse_natures()
        return self.natures_data.get(nature_id, f"Nature {nature_id}")

    def save_to_json(self, output_dir: str = "."):
        """Save parsed data to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save moves
        moves_file = output_path / "pokemon_moves.json"
        with open(moves_file, 'w', encoding='utf-8') as f:
            json.dump(self.moves_data, f, indent=2, ensure_ascii=False)
        
        # Save species
        species_file = output_path / "pokemon_species.json"
        with open(species_file, 'w', encoding='utf-8') as f:
            json.dump(self.species_data, f, indent=2, ensure_ascii=False)
        
        # Save character map
        charmap_file = output_path / "pokemon_charmap.json"
        with open(charmap_file, 'w', encoding='utf-8') as f:
            json.dump(self.char_map_data, f, indent=2, ensure_ascii=False)
            
        # Save natures
        natures_file = output_path / "pokemon_natures.json"
        with open(natures_file, 'w', encoding='utf-8') as f:
            json.dump(self.natures_data, f, indent=2, ensure_ascii=False)
            
        print(f"Saved {len(self.moves_data)} moves to {moves_file}")
        print(f"Saved {len(self.species_data)} species to {species_file}")
        print(f"Saved {len(self.char_map_data)} characters to {charmap_file}")
        print(f"Saved {len(self.natures_data)} natures to {natures_file}")

if __name__ == "__main__":
    # Example usage
    parser = PokemonDataParser(".")
    
    # Parse data
    moves = parser.parse_moves()
    species = parser.parse_species()
    char_map = parser.parse_char_map()
    natures = parser.parse_natures()
    
    print(f"Parsed {len(moves)} moves, {len(species)} species, {len(char_map)} characters, and {len(natures)} natures")
    
    # Test some lookups
    print(f"Move 446: {parser.get_move_name(446)}")  # Should be Stealth Rock
    print(f"Move 157: {parser.get_move_name(157)}")  # Should be Rock Slide
    print(f"Species 208: {parser.get_species_name(208)}")  # Should be Steelix
    print(f"Char 0xBB: '{parser.get_char_map(0xBB)}'")  # Should be 'A'
    print(f"Char 0xA1: '{parser.get_char_map(0xA1)}'")  # Should be '0'
    print(f"Nature 3: {parser.get_nature_name(3)}")  # Should be Adamant
    print(f"Nature 10: {parser.get_nature_name(10)}")  # Should be Timid
    
    # Save to JSON files
    parser.save_to_json()
