#!/usr/bin/env python3

from typing import List, Tuple
import ctypes
from parse_save import PokemonSaveParser, DEFAULT_SAVE_PATH, PokemonData

# ANSI color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
RESET = '\033[0m'


def display_colored_bytes(raw_bytes: bytes, 
                         colored_ranges: List[Tuple[int, int, str]], 
                         label: str = "") -> None:
    """
    Display bytes in a formatted way with colored sections and optional label.
    
    Args:
        raw_bytes: The byte array to display
        colored_ranges: List of tuples (start_idx, end_idx, color) where:
                       - start_idx: Starting byte index (inclusive)
                       - end_idx: Ending byte index (exclusive)
                       - color: ANSI color code (e.g., RED, GREEN, etc.)
        label: Optional label to display above the bytes
    """
    if label:
        print(f"{label}:")
        print()
    
    # Create the diagram above the bytes for each colored range
    line_above = ""
    for i in range(len(raw_bytes)):
        # Check if this byte is in any colored range
        in_colored_range = False
        for start_idx, end_idx, color in colored_ranges:
            if start_idx <= i < end_idx:
                if i == start_idx:
                    line_above += f"{color}┌─{RESET}"
                elif i == end_idx - 1:
                    line_above += f"{color}─┐{RESET}"
                else:
                    line_above += f"{color}──{RESET}"
                    
                # check if is not after the last byte of the range
                in_colored_range = True
                break
        
        if not in_colored_range:
            line_above += "--"
        
        # Add space after each position except the last
        if i < len(raw_bytes) - 1:
            if in_colored_range:
                line_above += f"┴"
            else:
                line_above += " "
    
    # Print the diagram
    if any(colored_ranges):  # Only print if there are colored ranges
        print(line_above)
    
    # Create the colored byte array
    byte_array: List[str] = []
    for i, b in enumerate(raw_bytes):
        # Check if this byte should be colored
        colored = False
        for start_idx, end_idx, color in colored_ranges:
            if start_idx <= i < end_idx:
                byte_array.append(f"{color}{b:02x}{RESET}")
                colored = True
                break
        
        if not colored:
            byte_array.append(f"{b:02x}")
    
    print(f"{' '.join(byte_array)}")
    print()


def display_simple_colored_bytes(raw_bytes: bytes, 
                                field_size: int, 
                                color: str = RED, 
                                label: str = "") -> None:
    """
    Simplified version that colors the first N bytes.
    
    Args:
        raw_bytes: The byte array to display
        field_size: Number of bytes from the start to color
        color: ANSI color code for the first field
        label: Optional label to display above the bytes
    """
    colored_ranges = [(0, field_size, color)] if field_size > 0 else []
    display_colored_bytes(raw_bytes, colored_ranges, label)


def main() -> None:
    """Simple byte array log of party Pokemon."""
    
    # Parse the save file
    save_parser = PokemonSaveParser(DEFAULT_SAVE_PATH)
    save_data = save_parser.parse_save_file()
    party_pokemon = save_data['party_pokemon']
    
    # Get the size of the first field dynamically from the struct
    first_field_name = PokemonData._fields_[0][0]  # Get field name
    first_field_type = PokemonData._fields_[0][1]  # Get field type
    first_field_size = ctypes.sizeof(first_field_type)
    
    print(f"First field: '{first_field_name}' ({first_field_size} bytes)")
    print()
    
    # Display simple byte arrays using the reusable function
    for slot, pokemon in enumerate(party_pokemon, 1):
        display_simple_colored_bytes(
            pokemon.raw_bytes, 
            first_field_size, 
            RED, 
            f"Slot {slot}"
        )


def example_usage() -> None:
    """Example of how to use the reusable functions with different colors and ranges."""
    # Example byte data
    example_bytes = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x11, 0x22])
    
    # Example 1: Simple coloring of first 4 bytes
    print("Example 1: Simple coloring")
    display_simple_colored_bytes(example_bytes, 4, GREEN, "First 4 bytes in green")
    
    # Example 2: Multiple colored ranges
    print("Example 2: Multiple colored ranges")
    colored_ranges = [
        (0, 2, RED),      # First 2 bytes in red
        (4, 6, BLUE),     # Bytes 4-5 in blue  
        (8, 10, YELLOW)   # Last 2 bytes in yellow
    ]
    display_colored_bytes(example_bytes, colored_ranges, "Multiple colored sections")


if __name__ == "__main__":
    main()
    
    # Uncomment the line below to see example usage
    example_usage()
