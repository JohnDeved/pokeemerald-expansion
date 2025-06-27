# Parsing Pokémon IV and EV Data from a Save File

This guide is intended for developers who want to write a parser to extract Pokémon IV and EV data directly from a *pokeemerald-expansion* save file. It provides Python examples to illustrate the process.

**Disclaimer:** Direct save file manipulation is risky. This guide is for educational purposes, and any damage to your save file is your own responsibility. Always back up your saves before attempting to parse or modify them.

## The `BoxPokemon` Structure

The fundamental data structure for a stored Pokémon is `BoxPokemon`. It contains all the essential information about a Pokémon, including its personality, OT, nickname, and its stats, which are stored in an encrypted and shuffled format.

Here is a simplified Python representation of the relevant parts of the `BoxPokemon` structure:

```python
# This is a conceptual representation. You will need to handle byte-level parsing.
class BoxPokemon:
    def __init__(self, data):
        # data is a 48-byte block for a single Pokémon
        self.personality = int.from_bytes(data[0:4], 'little')
        self.otId = int.from_bytes(data[4:8], 'little')
        # ... other fields ...
        self.checksum = int.from_bytes(data[30:32], 'little')
        self.secure_data = data[32:80] # The 48-byte encrypted block
```

## Substructure Shuffling and Decryption

The most complex part of parsing Pokémon data is handling the `secure` data block. This 48-byte block contains four 12-byte substructures that are shuffled and then encrypted with a key derived from the Pokémon's personality and OT ID.

### 1. Determining the Substructure Order

The order of the four substructures (`substruct0`, `substruct1`, `substruct2`, `substruct3`) is determined by the Pokémon's personality value modulo 24. The game uses a lookup table to determine the order.

Here is a Python implementation to get the correct order:

```python
SHUFFLE_TABLE = [
    [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2], [0, 2, 3, 1], [0, 3, 2, 1],
    [1, 0, 2, 3], [1, 0, 3, 2], [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
    [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2], [2, 3, 0, 1], [3, 2, 0, 1],
    [1, 2, 3, 0], [1, 3, 2, 0], [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0],
]

def get_substructure_order(personality):
    return SHUFFLE_TABLE[personality % 24]
```

### 2. Decrypting the Substructures

Each 12-byte substructure is encrypted by XORing it with a 32-bit key derived from the Pokémon's personality and OT ID. The key is applied to each 32-bit word of the substructure.

```python
def decrypt_substructures(encrypted_data, personality, otId):
    decryption_key = personality ^ otId
    decrypted_data = bytearray()

    for i in range(0, len(encrypted_data), 4):
        word = int.from_bytes(encrypted_data[i:i+4], 'little')
        decrypted_word = word ^ decryption_key
        decrypted_data.extend(decrypted_word.to_bytes(4, 'little'))

    return decrypted_data
```

## Parsing IVs and EVs

Once the substructures are decrypted and correctly ordered, you can parse the IV and EV data.

*   **EVs** are in `substruct2`.
*   **IVs** are in `substruct3`.

Here's how to parse them:

```python
def parse_evs(substruct2_data):
    return {
        'hp': substruct2_data[0],
        'attack': substruct2_data[1],
        'defense': substruct2_data[2],
        'speed': substruct2_data[3],
        'sp_attack': substruct2_data[4],
        'sp_defense': substruct2_data[5],
    }

def parse_ivs(substruct3_data):
    # IVs are stored as bitfields within a 32-bit integer
    iv_data = int.from_bytes(substruct3_data[4:8], 'little')
    return {
        'hp': (iv_data >> 0) & 0x1F,
        'attack': (iv_data >> 5) & 0x1F,
        'defense': (iv_data >> 10) & 0x1F,
        'speed': (iv_data >> 15) & 0x1F,
        'sp_attack': (iv_data >> 20) & 0x1F,
        'sp_defense': (iv_data >> 25) & 0x1F,
    }
```

## Putting It All Together

Here is a complete example of how to parse the IVs and EVs from a raw 48-byte `secure` data block of a `BoxPokemon`.

```python
# (SHUFFLE_TABLE from above)

def get_substructure_order(personality):
    return SHUFFLE_TABLE[personality % 24]

def decrypt_substructures(encrypted_data, personality, otId):
    decryption_key = personality ^ otId
    decrypted_data = bytearray()
    for i in range(0, len(encrypted_data), 4):
        word = int.from_bytes(encrypted_data[i:i+4], 'little')
        decrypted_word = word ^ decryption_key
        decrypted_data.extend(decrypted_word.to_bytes(4, 'little'))
    return decrypted_data

def parse_pokemon_stats(secure_data, personality, otId):
    decrypted_data = decrypt_substructures(secure_data, personality, otId)
    order = get_substructure_order(personality)

    substructures = {}
    for i in range(4):
        start = i * 12
        substructures[order[i]] = decrypted_data[start:start+12]

    evs = parse_evs(substructures[2])
    ivs = parse_ivs(substructures[3])

    return {'ivs': ivs, 'evs': evs}

# --- Example Usage ---
# This is a placeholder for the actual data from a save file
# You would need to extract this 80-byte block for a specific Pokémon
# from your save file (e.g., from the PC boxes data).

# Example data (replace with actual data from your save file)
# This is NOT real data and is for illustrative purposes only.
personality = 0x12345678
otId = 0x87654321
# secure_data would be 48 bytes read from the save file
# For this example, we'll create some dummy encrypted data
secure_data = bytearray(48)

# In a real scenario, you would read the personality, otId, and secure_data
# directly from the save file.

# parsed_stats = parse_pokemon_stats(secure_data, personality, otId)
# print(parsed_stats)

```

This guide provides the fundamental logic for parsing IV and EV data. A complete save file parser would also need to locate the Pokémon data within the save file structure (e.g., in the player's party or PC boxes), which is beyond the scope of this document.
