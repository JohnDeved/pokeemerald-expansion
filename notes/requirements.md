# Pokemon Quetzal Save File Parser - LLM Instructions

## Project Overview
This project involves developing and refining a Python parser for Pokemon Quetzal ROM hack save files. The parser extracts party Pokemon data, player information, and other save file contents from the custom save format used by Pokemon Quetzal.

## Primary Objective
Implement and validate the correct Pokemon data structure in `parse_save.py` based on the ground truth specifications provided in `docs/quetzal_party_pokemon_struct.md`. The current implementation has incorrect field mappings and needs to be corrected to match the documented 104-byte structure.

## Current Status
- ✅ Basic save file loading and sector parsing works correctly
- ✅ Player name and playtime extraction implemented
- ❌ Missing proper substruct parsing for Pokemon data
- ❌ Not all fields in `PokemonData` are known and correctly mapped yet

## Detailed Task List

### 1. Fix PokemonData Structure (PRIORITY 1)
**Problem**: Current structure has incorrect field offsets and missing required fields.

**Action Required**:
- Replace the current `PokemonData` class with the correct 104-byte structure from `docs/quetzal_party_pokemon_struct.md`
- Implement proper field mappings:
  - 0x00-0x4E: Box Pokemon data (79 bytes)
  - 0x4F-0x67: Party-specific data (25 bytes)
- Add all missing fields including:
  - `personality` (u32 at 0x00)
  - `language` (u8 at 0x12) 
  - `markings` (u8 at 0x1A)
  - `checksum` (u16 at 0x1B)
  - `hpLost` (u16 at 0x1D)
  - `substructs` (48 bytes at 0x1F)
  - `mail` (u8 at 0x54)
  - Correct `currentHp` to u16 at 0x55

### 2. Implement Substruct Parsing (PRIORITY 2)
**Requirements**:
- Parse the 4 substructures (12 bytes each) within the 48-byte substruct data section
- **Note**: According to ground truth, Quetzal substructs are NOT encrypted (different from vanilla)
- Extract key Pokemon data:
  - **Substruct 0**: species, heldItem, experience, friendship, pokeball
  - **Substruct 1**: moves (1-4) and PP values
  - **Substruct 2**: EVs (HP, Atk, Def, Spe, SpA, SpD) and contest stats
  - **Substruct 3**: IVs, pokerus, met location/level, abilities, ribbons

### 3. Add Comprehensive Testing (PRIORITY 3)
**Test Requirements**:
- Verify field offsets match the documentation exactly
- Test with known save files to validate parsed data accuracy
- Add unit tests for individual Pokemon structure parsing
- Implement regression tests to prevent future breakage
- Add hex dump comparison tools for debugging

### 4. Enhance Parser Features (PRIORITY 4)
**Nice-to-have additions**:
- Add Box Pokemon parsing (not just party)
- Implement trainer card data extraction
- Add Pokedex data parsing
- Support for additional Quetzal-specific features
- Better error handling and validation

## Technical Constraints & Guidelines

### Code Standards
- Use Python 3.7+ with type hints
- Follow ctypes.Structure best practices for binary data
- Maintain backward compatibility with existing CLI interface
- Keep JSON output format stable
- Add comprehensive docstrings and comments

### Validation Requirements
- All byte offsets must match `docs/quetzal_party_pokemon_struct.md` exactly
- Test parsing with actual save files from Pokemon Quetzal
- Verify decoded strings use correct character encoding
- Ensure stat calculations are accurate for party Pokemon

### Important Notes
- **ROM Hack Differences**: Pokemon Quetzal uses a modified save format different from vanilla Pokemon Emerald
- **No Assumptions**: Don't assume vanilla Pokemon structure applies - always refer to the ground truth data documentation
- **Offset Verification**: Every field offset must be validated against the documented structure
- **Substruct Order**: Verify if Quetzal uses fixed substruct order (0,1,2,3) or PID-based ordering

## Development Workflow

### Step 1: Structure Analysis
1. Read and understand `docs/quetzal_party_pokemon_struct.md` completely
2. Compare current implementation against ground truth
3. Document all discrepancies and missing fields

### Step 2: Implementation
1. Rewrite `PokemonData` class with correct field mappings
2. Add substruct classes for the 4 data substructures
3. Implement parsing logic for substruct data sections
4. Update all related parsing methods

### Step 3: Validation
1. Test with known save files
2. Compare parsed output with hex dumps
3. Verify all statistics and data accuracy
4. Add regression tests

### Step 4: Documentation
1. Update code comments with correct field descriptions
2. Document any Quetzal-specific discoveries
3. Update this requirements file with progress

## Progress Tracking
- [ ] PokemonData structure corrected
- [ ] Substruct parsing implemented  
- [ ] Testing framework added
- [ ] All fields validated against ground truth
- [ ] Documentation updated

## Files to Modify
- `parse_save.py` - Main parser implementation
- `requirements.md` - This file (keep updated)
- Add test files as needed

## Reference Materials
- Vanilla Pokemon structures (see below) - For comparison only, NOT for implementation
- Existing codebase - For general patterns but NOT for specific offsets

**Remember**: The Quetzal ground truth document is authoritative. The vanilla structures below are for conceptual understanding only - ROM hacks like Quetzal have different offsets, field orders, and sizes even for similar data.

## Important Note About ROM Hack Differences
Pokemon Quetzal significantly modifies the save file structure compared to vanilla Pokemon Emerald. **Do not assume any field is at the same offset or has the same size as vanilla.** Even basic fields like `currentHp` are at completely different locations. Always refer to the Quetzal-specific documentation for implementation.

## Vanilla Pokemon Structures (Reference Only)
*These are the standard Pokemon Emerald structures for CONCEPTUAL REFERENCE ONLY. DO NOT use these offsets, field orders, or sizes for Quetzal implementation - they are different!*

**⚠️ DO NOT MODIFY OR IMPLEMENT THESE STRUCTURES.**
These C data structures are included solely to illustrate how the vanilla game organizes Pokemon data. Our task is to reverse-engineer and document the equivalent structure for Pokemon Quetzal, which is known to differ. All Quetzal implementation must be based on Quetzal-specific documentation, save file analysis, and codebase investigation—not on these vanilla structures.*

**Do not change or use these C structs for Quetzal parsing.**

### Standard Pokemon Structure (Vanilla)
```c
struct Pokemon
{
    struct BoxPokemon box;
    u32 status;
    u8 level;
    u8 mail;
    u16 hp;
    u16 maxHP;
    u16 attack;
    u16 defense;
    u16 speed;
    u16 spAttack;
    u16 spDefense;
};
```

### Standard BoxPokemon Structure (Vanilla)
```c
struct BoxPokemon
{
    u32 personality;
    u32 otId;
    u8 nickname[min(10, POKEMON_NAME_LENGTH)];
    u8 language:3;
    u8 hiddenNatureModifier:5; // 31 natures.
    u8 isBadEgg:1;
    u8 hasSpecies:1;
    u8 isEgg:1;
    u8 blockBoxRS:1; // Unused, but Pokémon Box Ruby & Sapphire will refuse to deposit a Pokémon with this flag set.
    u8 daysSinceFormChange:3; // 7 days.
    u8 unused_13:1;
    u8 otName[PLAYER_NAME_LENGTH];
    u8 markings:4;
    u8 compressedStatus:4;
    u16 checksum;
    u16 hpLost:14; // 16383 HP.
    u16 shinyModifier:1;
    u16 unused_1E:1;

    union
    {
        u32 raw[(NUM_SUBSTRUCT_BYTES * 4) / 4]; // *4 because there are 4 substructs, /4 because it's u32, not u8
        union PokemonSubstruct substructs[4];
    } secure;
};
```

### Standard Substruct Union (Vanilla)
```c
// Number of bytes in the largest Pokémon substruct.
// They are assumed to be the same size, and will be padded to
// the largest size by the union.
// By default they are all 12 bytes.
#define NUM_SUBSTRUCT_BYTES (max(sizeof(struct PokemonSubstruct0),     \
                             max(sizeof(struct PokemonSubstruct1),     \
                             max(sizeof(struct PokemonSubstruct2),     \
                                 sizeof(struct PokemonSubstruct3)))))

union PokemonSubstruct
{
    struct PokemonSubstruct0 type0;
    struct PokemonSubstruct1 type1;
    struct PokemonSubstruct2 type2;
    struct PokemonSubstruct3 type3;
    u16 raw[NUM_SUBSTRUCT_BYTES / 2]; // /2 because it's u16, not u8
};
```

### Standard Substruct 0 (Vanilla) - Growth Data
```c
struct PokemonSubstruct0
{
    u16 species:11; // 2047 species.
    u16 teraType:5; // 30 types.
    u16 heldItem:10; // 1023 items.
    u16 unused_02:6;
    u32 experience:21;
    u32 nickname11:8; // 11th character of nickname.
    u32 unused_04:3;
    u8 ppBonuses;
    u8 friendship;
    u16 pokeball:6; // 63 balls.
    u16 nickname12:8; // 12th character of nickname.
    u16 unused_0A:2;
};
```

### Standard Substruct 1 (Vanilla) - Moves Data
```c
struct PokemonSubstruct1
{
    u16 move1:11; // 2047 moves.
    u16 evolutionTracker1:5;
    u16 move2:11; // 2047 moves.
    u16 evolutionTracker2:5;
    u16 move3:11; // 2047 moves.
    u16 unused_04:5;
    u16 move4:11; // 2047 moves.
    u16 unused_06:3;
    u16 hyperTrainedHP:1;
    u16 hyperTrainedAttack:1;
    u8 pp1:7; // 127 PP.
    u8 hyperTrainedDefense:1;
    u8 pp2:7; // 127 PP.
    u8 hyperTrainedSpeed:1;
    u8 pp3:7; // 127 PP.
    u8 hyperTrainedSpAttack:1;
    u8 pp4:7; // 127 PP.
    u8 hyperTrainedSpDefense:1;
};
```

### Standard Substruct 2 (Vanilla) - EVs/Contest Data
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
```

### Standard Substruct 3 (Vanilla) - Misc Data
```c
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
    u32 coolRibbon:3;     // Stores the highest contest rank achieved in the Cool category.
    u32 beautyRibbon:3;   // Stores the highest contest rank achieved in the Beauty category.
    u32 cuteRibbon:3;     // Stores the highest contest rank achieved in the Cute category.
    u32 smartRibbon:3;    // Stores the highest contest rank achieved in the Smart category.
    u32 toughRibbon:3;    // Stores the highest contest rank achieved in the Tough category.
    u32 championRibbon:1; // Given when defeating the Champion.
    u32 winningRibbon:1;  // Given at the Battle Tower's Level 50 challenge.
    u32 victoryRibbon:1;  // Given at the Battle Tower's Level 100 challenge.
    u32 artistRibbon:1;   // Given at the Contest Hall by winning a Master Rank contest.
    u32 effortRibbon:1;   // Given at Slateport's market to Pokémon with maximum EVs.
    u32 marineRibbon:1;   // Never distributed.
    u32 landRibbon:1;     // Never distributed.
    u32 skyRibbon:1;      // Never distributed.
    u32 countryRibbon:1;  // Distributed during Pokémon Festa '04 and '05.
    u32 nationalRibbon:1; // Given to purified Shadow Pokémon in Colosseum/XD.
    u32 earthRibbon:1;    // Given to teams that have beaten Mt. Battle's 100-battle challenge.
    u32 worldRibbon:1;    // Distributed during Pokémon Festa '04 and '05.
    u32 isShadow:1;
    u32 unused_0B:1;
    u32 abilityNum:2;
    u32 modernFatefulEncounter:1;
};
```

### Key Differences: Vanilla vs Quetzal
**⚠️ CRITICAL**: Pokemon Quetzal uses a completely different structure layout. The vanilla structures above are provided ONLY for general conceptual understanding. Key differences include:

1. **Different Field Orders**: Quetzal reorders many fields compared to vanilla
2. **Different Offsets**: Even identical fields are at different byte positions (e.g., currentHp)
3. **Different Sizes**: Some fields may be larger/smaller in Quetzal
4. **Additional Fields**: Quetzal may have ROM hack-specific fields not in vanilla
5. **Different Encryption**: Substructs may not be encrypted in Quetzal
6. **Extended Features**: Quetzal includes features not in vanilla (forms, abilities, etc.)
7. **Bit-field Differences**: Packed fields may use different bit layouts

**EXAMPLE OF CRITICAL DIFFERENCES**:
- Vanilla party Pokemon structure has `currentHp` at one location
- Quetzal ground truth documents `currentHp` (u16) at offset 0x55
- Using vanilla offsets would read completely wrong data!

**Always refer to `docs/quetzal_party_pokemon_struct.md` for the correct Quetzal implementation. The vanilla structures are only for understanding conceptual relationships between data types.**

## Current Parser Output Analysis

### Working Test Data (Last Run: 2025-06-28)
The parser currently works with a save file containing 6 party Pokemon:

```
Active save slot: 0
Valid sectors found: 14
Player Name: John
Play Time: 44h 23m 29s

Party Pokemon:
1. Steelix (ID: 208) - Level 44 - HP: 0/131 [FAINTED]
2. Breloom (ID: 286) - Level 45 - HP: 126/126 [HEALTHY]
3. Snorlax (ID: 143) - Level 47 - HP: 248/248 [HEALTHY]
4. Ludicolo (ID: 272) - Level 45 - HP: 135/135 [HEALTHY] 
5. Rayquaza (ID: 6) - Level 41 - HP: 132/132 [HEALTHY]
6. Sigilyph (ID: 561) - Level 37 - HP: 114/114 [HEALTHY]
```

### Critical Issues Identified

1. **HP Field Problem**: Steelix shows 0/131 HP but should show current HP properly
   - According to ground truth: `currentHp` should be u16 at offset 0x55
   - Current implementation incorrectly maps this field

2. **Missing Data Fields**: The parser shows basic stats but missing:
   - Moves and PP
   - EVs and IVs  
   - Experience points
   - Held items
   - Nature (shows some natures but likely incorrect due to wrong personality mapping)
   - Abilities
   - Contest stats

3. **Species ID Verification**: Species IDs appear correct (Rayquaza=6, Sigilyph=561), suggesting some parsing works

### Raw Byte Analysis Sample
First Pokemon (Steelix) raw bytes:
```
e4 00 00 00 0a 20 6c d4 cd e8 d9 d9 e0 dd ec ff 00 00 02 02 c4 e3 dc e2 ff ff ff 00 00 00 00 00 00 01 00 00 00 00 00 04 d0 00 d8 01 08 38 01 00 ff 0b 01 00 be 01 9d 00 5b 00 a7 01 20 0e 0f 18 4c 5c 08 fc 3c 14 00 00 00 00 00 00 00 00 00 00 28 a1 15 12 00 00 00 50 2c ff 83 00 66 00 b9 00 3f 00 36 00 44 00 cc cd
```

**Key Observations**:
- Bytes 0x00-0x03: `e4 00 00 00` = Personality value (228)
- Bytes 0x04-0x07: `0a 20 6c d4` = OT ID  
- Bytes 0x08-0x11: Pokemon nickname (encoded)
- The structure needs complete remapping to match ground truth

### the *Ground Truth* ingame display Data (from user) for player1.sav

**First pokémon in party Ground Truth (Steelix):**
*   **Pokémon:** Steelix, LVL 44, Male, Adamant Nature, Sturdy Ability
*   **OT:** John, **IDNo:** 08202
*   **Stats:** HP 0/131, Atk 102, Def 185, Spd 63, Sp.Atk 54, Sp.Def 68
*   **Item:** Leftovers
*   **Moves:** Stealth Rock, Rock Slide, Dig, Ice Fang

This data should be used to validate the parser implementation. The current parser shows incorrect data for some fields.

### Validation Requirements
The corrected parser must produce output matching the above ground truth data exactly:
- Nature should be "Adamant" (derived from personality value)
- Current HP should be 0 (fainted)
- Max HP should be 131
- All stats should match exactly
- Item should be identified as Leftovers
- All 4 moves should be parsed correctly

### Immediate Action Items

1. **Fix Structure Mapping**: Current `PokemonData` class has completely wrong field offsets
2. **Implement Substruct Parsing**: The 48-byte substruct section (0x1F-0x4E) needs proper parsing
4. **Add Missing Fields**: find all fields in the struct

### Progress Log
- **2025-06-28**: Initial analysis completed

---

## Work History & Updates
*Keep this section updated with all changes made to the parser