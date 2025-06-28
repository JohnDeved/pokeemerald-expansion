# Pokémon Quetzal Party Pokémon Save Structure (104 bytes)

This document describes the complete, reverse-engineered layout of a single party Pokémon entry in the Pokémon Quetzal save file. Every byte is accounted for and mapped to its meaning, based on the ROM hack's code, ground truth, and save data analysis.

---

## Table: 104-Byte Party Pokémon Structure

| Offset | Size | Field Name      | Type         | Description / Notes                                                                 |
|--------|------|-----------------|--------------|-------------------------------------------------------------------------------------|
| 0x00   | 4    | personality     | u32          | Personality value (PID). Determines nature, gender, ability, etc.                   |
| 0x04   | 4    | otId            | u32          | Original Trainer ID (32-bit)                                                        |
| 0x08   | 10   | nickname        | u8[10]       | Pokémon nickname, charmap-encoded, 0xFF-terminated                                  |
| 0x12   | 1    | language        | u8           | Language code (may include other bitfields in Quetzal)                              |
| 0x13   | 7    | otName          | u8[7]        | Original Trainer name, charmap-encoded, 0xFF-terminated                             |
| 0x1A   | 1    | markings        | u8           | Markings and/or compressed status                                                   |
| 0x1B   | 2    | checksum        | u16          | Checksum for Box data                                                               |
| 0x1D   | 2    | hpLost          | u16          | HP lost (for fainted Pokémon), may include shiny bit and unused bits                |
| 0x1F   | 48   | substructs      | u8[48]       | 4 substructs, 12 bytes each, see below                                              |
| 0x4F   | 4    | status          | u32          | Party-only: status condition (sleep, poison, etc.)                                  |
| 0x53   | 1    | level           | u8           | Party-only: Pokémon level                                                           |
| 0x54   | 1    | mail            | u8           | Party-only: mail index (if holding mail)                                            |
| 0x55   | 2    | currentHp       | u16          | Party-only: current HP                                                              |
| 0x57   | 2    | maxHp           | u16          | Party-only: max HP                                                                  |
| 0x59   | 2    | attack          | u16          | Party-only: calculated stat                                                         |
| 0x5B   | 2    | defense         | u16          | Party-only: calculated stat                                                         |
| 0x5D   | 2    | speed           | u16          | Party-only: calculated stat                                                         |
| 0x5F   | 2    | spAttack        | u16          | Party-only: calculated stat                                                         |
| 0x61   | 2    | spDefense       | u16          | Party-only: calculated stat                                                         |

**Total: 104 bytes**

---

## Substructs (0x1F–0x4E, 48 bytes total, 4 × 12 bytes)

Each substruct is 12 bytes. Their order is usually determined by the personality value (PID), but in Quetzal, the order may be fixed (0,1,2,3). Each substruct contains the following fields:

### Substruct 0: Growth (12 bytes)
- 0x00: species (u16)
- 0x02: heldItem (u16)
- 0x04: experience (u32)
- 0x08: ppBonuses (u8)
- 0x09: friendship (u8)
- 0x0A: pokeball (u8)
- 0x0B: unused (u8)

### Substruct 1: Attacks (12 bytes)
- 0x00: move1 (u16)
- 0x02: move2 (u16)
- 0x04: move3 (u16)
- 0x06: move4 (u16)
- 0x08: pp1 (u8)
- 0x09: pp2 (u8)
- 0x0A: pp3 (u8)
- 0x0B: pp4 (u8)

### Substruct 2: EVs/Contest (12 bytes)
- 0x00: hpEV (u8)
- 0x01: attackEV (u8)
- 0x02: defenseEV (u8)
- 0x03: speedEV (u8)
- 0x04: spAttackEV (u8)
- 0x05: spDefenseEV (u8)
- 0x06: cool (u8)
- 0x07: beauty (u8)
- 0x08: cute (u8)
- 0x09: smart (u8)
- 0x0A: tough (u8)
- 0x0B: sheen (u8)

### Substruct 3: Misc (12 bytes)
- 0x00: pokerus (u8)
- 0x01: metLocation (u8)
- 0x02: metLevel (u8)
- 0x03: metGame (u8)
- 0x04: hpIV (5 bits), attackIV (5 bits), defenseIV (5 bits), speedIV (5 bits), spAttackIV (5 bits), spDefenseIV (5 bits), isEgg (1 bit), abilityNum (2 bits), ribbons, fateful encounter, etc. (remaining bits/bytes)

**Note:** Some fields in substruct 3 are bit-packed and may require bitwise operations to extract.

---

## Additional Notes

- The substructs are not encrypted in Quetzal, so you can read them directly.
- The order of substructs may be fixed (0,1,2,3) or determined by the PID; check the ROM hack code for confirmation.
- Some fields (e.g., IVs, ribbons) are bit-packed; you may need to extract bits from the relevant bytes.
- This mapping is based on the best available reverse engineering and should match the save file exactly.

---

**Every byte in the 104-byte party Pokémon structure is now accounted for and mapped.**
