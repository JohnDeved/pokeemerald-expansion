# How Pokémon IV/EV Stats Are Handled in the Save File

This document explains how Individual Values (IVs) and Effort Values (EVs) for Pokémon are read from and written to the save file within the pokeemerald-expansion codebase.

## Understanding IVs and EVs

*   **Individual Values (IVs)**: These are inherent, unchangeable values assigned to a Pokémon when it is generated. They range from 0 to 31 for each of the six stats (HP, Attack, Defense, Speed, Special Attack, Special Defense) and contribute significantly to a Pokémon's final stats.
*   **Effort Values (EVs)**: These are points gained by a Pokémon through battling other Pokémon. Each Pokémon can gain a maximum of 510 total EVs, with a cap of 252 EVs per individual stat. EVs directly increase a Pokémon's stats.

## Data Storage in the Save File

Pokémon data, including IVs and EVs, is primarily stored within the `struct BoxPokemon` structure. This structure is a core component of how Pokémon are represented in the game's memory and, consequently, in the save file.

The `BoxPokemon` structure contains a `secure` union, which is a critical element for understanding data storage. This `secure` union holds four different `PokemonSubstruct` unions (`type0` through `type3`). The game uses these substructures to store various pieces of Pokémon data, often in an obfuscated or shuffled manner to prevent direct manipulation of save files.

Specifically, IVs and EVs are located within these substructures:

*   **Effort Values (EVs)**: Stored in `struct PokemonSubstruct2`. This substructure contains fields like `hpEV`, `attackEV`, `defenseEV`, `speedEV`, `spAttackEV`, and `spDefenseEV`.
*   **Individual Values (IVs)**: Stored in `struct PokemonSubstruct3`. This substructure contains fields like `hpIV`, `attackIV`, `defenseIV`, `speedIV`, `spAttackIV`, and `spDefenseIV`.

### Relevant C Structures

Here are the relevant C struct definitions from `include/pokemon.h`:

```c
struct PokemonSubstruct2
{
    u8 hpEV;
    u8 attackEV;
    u8 defenseEV;
    u8 speedEV;
    u8 spAttackEV;
    u8 spDefenseEV;
    u8 cool;
    u8 beauty;
    u8 cute;
    u8 smart;
    u8 tough;
    u8 sheen;
};

struct PokemonSubstruct3
{
    u8 pokerus;
    u8 metLocation;
    u16 metLevel:7;
    u16 metGame:4;
    u16 dynamaxLevel:4;
    u16 otGender:1;
    u32 hpIV:5;
    u32 attackIV:5;
    u32 defenseIV:5;
    u32 speedIV:5;
    u32 spAttackIV:5;
    u32 spDefenseIV:5;
    u32 isEgg:1;
    u32 gigantamaxFactor:1;
    // ... other ribbon and flag data
};

struct BoxPokemon
{
    u32 personality;
    u32 otId;
    // ... other data
    union
    {
        u32 raw[(NUM_SUBSTRUCT_BYTES * 4) / 4];
        union PokemonSubstruct substructs[4];
    } secure;
};
```

## Data Encryption and Shuffling

To deter save file manipulation, the game encrypts and shuffles the four `PokemonSubstruct` unions within the `secure` union of the `BoxPokemon` structure. The order of the substructures is determined by the Pokémon's 32-bit personality value.

The functions `EncryptBoxMon` and `DecryptBoxMon` in `src/pokemon.c` handle this process. `EncryptBoxMon` is called when a Pokémon is created or modified, and `DecryptBoxMon` is used when the game needs to access the raw data.

## Reading Stats: `GetMonData`

The game uses the `GetMonData` function (and its `BoxMon` counterpart, `GetBoxMonData`) to retrieve specific data points from a Pokémon's structure. This function takes a `Pokemon` or `BoxPokemon` pointer and a `MON_DATA_` constant as arguments to specify which piece of data to retrieve.

Here are some examples of `MON_DATA_` constants used for IVs and EVs:

*   `MON_DATA_HP_IV`
*   `MON_DATA_ATK_IV`
*   `MON_DATA_DEF_IV`
*   `MON_DATA_SPEED_IV`
*   `MON_DATA_SPATK_IV`
*   `MON_DATA_SPDEF_IV`
*   `MON_DATA_HP_EV`
*   `MON_DATA_ATK_EV`
*   `MON_DATA_DEF_EV`
*   `MON_DATA_SPEED_EV`
*   `MON_DATA_SPATK_EV`
*   `MON_DATA_SPDEF_EV`

**Example Usage (Conceptual):**

```c
// To get a Pokémon's HP IV
u32 hp_iv = GetMonData(myPokemon, MON_DATA_HP_IV);

// To get a Pokémon's Attack EV
u32 atk_ev = GetMonData(myPokemon, MON_DATA_ATK_EV);
```

## Writing Stats: `SetMonData`

Similarly, the `SetMonData` function (and `SetBoxMonData`) is used to write data to a Pokémon's structure. It takes a `Pokemon` or `BoxPokemon` pointer, a `MON_DATA_` constant, and a pointer to the data to be written.

**Example Usage (Conceptual):**

```c
// To set a Pokémon's HP IV to 31
u32 new_hp_iv = 31;
SetMonData(myPokemon, MON_DATA_HP_IV, &new_hp_iv);

// To set a Pokémon's Attack EV to 252
u32 new_atk_ev = 252;
SetMonData(myPokemon, MON_DATA_ATK_EV, &new_atk_ev);
```

## Stat Calculation: `CalculateMonStats`

The `CalculateMonStats` function, located in `src/pokemon.c`, is responsible for calculating a Pokémon's final stats based on its base stats, IVs, EVs, level, and nature. This function is called whenever a Pokémon is created, leveled up, or its stats are otherwise modified.

The core of the stat calculation is the following formula:

```c
// For HP:
newMaxHP = (((2 * baseStat + iv + ev / 4) * level) / 100) + level + 10;

// For other stats:
n = (((2 * baseStat + iv + ev / 4) * level) / 100) + 5;
n = ModifyStatByNature(nature, n, statIndex);
```

Where:

*   `baseStat` is the Pokémon's base stat for a particular attribute.
*   `iv` is the Individual Value for that stat.
*   `ev` is the Effort Value for that stat.
*   `level` is the Pokémon's current level.
*   `nature` is the Pokémon's nature, which can increase one stat by 10% and decrease another by 10%.
*   `statIndex` is the index of the stat being calculated.

## Save File Interaction

The `GetMonData` and `SetMonData` functions operate on the in-memory `Pokemon` and `BoxPokemon` structures. The game's save system is responsible for taking these in-memory structures and writing them to the persistent save file on the game cartridge or emulator. When the game loads, it reads the data from the save file and populates these in-memory structures.

**Important Note:** Due to the use of the `secure` union and potential data obfuscation/encryption within the `BoxPokemon` structure, directly editing the save file without a thorough understanding of the game's internal data handling and encryption mechanisms is highly discouraged and can lead to save file corruption. The `GetMonData` and `SetMonData` functions abstract away these complexities, providing a safe and intended way to interact with Pokémon data.