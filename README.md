# Planar Personas

A Python script for finding Magic: The Gathering characters and their card references via the Scryfall API.

# Basic usage
`python main.py > output.txt`

## How it works
1. Get Planeswalker/Legendary Names:
   - First checks cache for list of planeswalkers
   - If not found, fetches from Scryfall API
   - Stores in `mtg_cache/planeswalker_names.json`

2. Get All Legendary Creatures:
   - Checks cache for list of legendary creatures
   - If not found, fetches from Scryfall API
   - Stores in `mtg_cache/legendary_creatures.json`

3. For Each Character:
   - Extract base name (e.g., "Jace" from "Jace, the Mind Sculptor")
   - Check cache for character's references (`references_jace.json`)
   - If not found, search Scryfall for all cards containing name
   - Filter out emblems and duplicates
   - Store results in cache

All cache files:
- `planeswalker_names.json` - List of all planeswalker names
- `legendary_creatures.json` - List of all legendary creatures
- `references_*.json` - Card references for each character
- Cache expires after 7 days