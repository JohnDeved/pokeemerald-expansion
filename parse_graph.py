#!/usr/bin/env python3

import sys
import argparse
from typing import List, Tuple
from parse_save import PokemonSaveParser, DEFAULT_SAVE_PATH

# Ensure UTF-8 output for Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

RESET = '\033[0m'

def display_colored_bytes(raw_bytes: bytes, colored_ranges: List[Tuple[int, int, str, str]], bytes_per_line: int = 32) -> None:
    get_field = lambda idx: next(((s, e, c, n) for s, e, c, n in colored_ranges if s <= idx < e), None)
    
    pos = 0
    while pos < len(raw_bytes):
        # Don't split colored ranges across lines
        line_end = min(pos + bytes_per_line, len(raw_bytes))
        for s, e, _, _ in colored_ranges:
            if pos < s < line_end < e: line_end = s; break
        if line_end == pos: line_end = min(next((e for s, e, _, _ in colored_ranges if s <= pos < e), pos + 1), len(raw_bytes))
        
        line_bytes = raw_bytes[pos:line_end]
        if not line_bytes: break
            
        lines, bytes_hex = ["", ""], []
        
        # Build label line first
        label_line = ""
        i = 0
        while i < len(line_bytes):
            idx = pos + i
            field = get_field(idx)
            
            if field and field[3] and idx == field[0]:
                # This is the start of a field
                field_bytes_in_line = min(field[1] - field[0], len(line_bytes) - i)
                width = field_bytes_in_line * 3 - 1
                name = field[3]
                if len(name) > width:
                    name = name[:width-1] + '.' if width > 0 else '.'
                label_line += f"{field[2]}{name.center(width)}{RESET}"
                
                # Skip to end of this field in this line
                i += field_bytes_in_line
                
                # Add space if there's more content after this field
                if i < len(line_bytes):
                    label_line += " "
            else:
                # Not a field start - add spacing
                label_line += "   " if i < len(line_bytes) - 1 else "  "
                i += 1
        
        lines[0] = label_line
        
        # Build ASCII art and hex
        for i, b in enumerate(line_bytes):
            idx, field = pos + i, get_field(pos + i)
            
            # ASCII art & hex
            if field:
                s, e, c = field[:3]
                if e - s == 1:  # Single byte field
                    art = "─┴"
                else:
                    art = "┌─" if idx == s else "─┐" if idx == e-1 else "┴─" if (e-s) % 2 == 1 and idx == s + (e-s)//2 else "──"
                lines[1] += f"{c}{art}{RESET}"
                bytes_hex.append(f"{c}{b:02x}{RESET}")
                
                # Space handling
                if i < len(line_bytes) - 1:
                    next_field = get_field(idx + 1)
                    space = ("┴" if (e-s) % 2 == 0 and idx == s + (e-s)//2 - 1 else
                            " " if next_field and next_field != field and next_field[0] == idx + 1 else
                            "─" if idx + 1 < e else " ")
                    lines[1] += f"{c if space in '┴─' else ''}{space}{RESET if space in '┴─' else ''}"
            else:
                lines[1] += "   " if i < len(line_bytes) - 1 else "  "
                bytes_hex.append(f"{b:02x}")
        
        # Output
        if lines[0].strip():  # If there are labels
            print()  # Add empty line for breathing room
        for line in lines:
            if line.strip(): print(f"      {line}")
        print(f"{pos:04x}: {' '.join(bytes_hex)}")
        pos = line_end

def main() -> None:
    parser = argparse.ArgumentParser(description="Parse and visualize Pokemon save file data")
    parser.add_argument("path", nargs="?", default=DEFAULT_SAVE_PATH,
                       help=f"Path to save file (default: {DEFAULT_SAVE_PATH})")
    args = parser.parse_args()
    
    save_data = PokemonSaveParser(args.path).parse_save_file()
    
    # Human-extendable field definitions: (name, offset, size)
    fields = [
        ("personality", 0, 4),
        ("otId", 4, 4),
        ("nickname", 8, 10),
        ("otName", 0x14, 7),
        ("c.HP", 0x23, 2),
        ("status", 0x25, 1),
        ("sp.Id", 0x28, 2),
        ("item", 0x2A, 2),
        ("moves", 0x34, 0x3F-0x34),
        ("EVS?", 0x40-1, 6),  # EVs from 0x40 to 0x58
        ("IV", 0x40+16, 4),
        ("lv", 0x58, 1),
        ("HP", 0x5A, 2),
        ("Atk", 0x5C, 2),
        ("Def", 0x5E, 2),
        ("S.Def", 0x60, 2),
        ("S.Atk", 0x62, 2),
        ("Speed", 0x64, 2),
    ]
    
    for slot, pokemon in enumerate(save_data['party_pokemon'], 1):
        print(f"Slot {slot} ({pokemon.nickname_str} #{pokemon.speciesId}):\n")
        display_colored_bytes(pokemon.raw_bytes, [(o, o + s, f'\033[{91+i % 6}m', n) for i, (n, o, s) in enumerate(fields)])
        print("\n" + "-" * 80 + "\n")

if __name__ == "__main__":
    main()
