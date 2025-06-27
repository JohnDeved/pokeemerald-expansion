# Plan for Parsing IVs and EVs from a Pokémon Quetzal Save File

This document outlines a structured plan to reverse-engineer the IV and EV data storage within a Pokémon Quetzal save file.

## Ground Truth Data (from user) for player1.sav

first pokémon in party:
*   **Pokémon:** Steelix, LVL 44, Male, Adamant Nature, Sturdy Ability
*   **OT:** John, **IDNo:** 08202 (`0x200A`)
*   **Stats:** HP 0/131, Atk 102, Def 185, Spd 63, Sp.Atk 54, Sp.Def 68
*   **Item:** Leftovers
*   **Moves:** Stealth Rock, Rock Slide, Dig, Ice Fang