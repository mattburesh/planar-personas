import requests
import time
import re
import json
import os
import logging
from collections import defaultdict
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('character_search.log'),
        logging.StreamHandler()
    ]
)

class MTGCharacterFinder:
    def __init__(self, cache_dir="mtg_cache"):
        self.base_url = "https://api.scryfall.com"
        self.characters = defaultdict(set)
        self.cache_dir = cache_dir
        self.cache_dur = timedelta(days=7)

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _get_cache_path(self, cache_type):
        """Get the path for a specific file."""
        return os.path.join(self.cache_dir, f"{cache_type}.json")
    
    def _load_cache(self, cache_type):
        """Load data from cache if it exists and isn't expired."""
        cache_path = self._get_cache_path(cache_type)
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            cache_date = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_date <= self.cache_dur:
                return cache_data['data']
        return None
    
    def _save_cache(self, cache_type, data):
        """Save data to cache with timestamp."""
        cache_path = self._get_cache_path(cache_type)
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

    def get_legendary_creatures(self):
        """Fetch all legendary creatures, using cache if available."""
        cached_data = self._load_cache('legendary_creatures')
        if cached_data is not None:
            logging.info("Using cached legendary creatures data")
            return cached_data
        
        print("Fetching legendary creatures from Scryfall...")
        url = f"{self.base_url}/cards/search"
        params = {
            'q': '(type:legendary type:creatures) or type:planeswalker',
            'unique': 'cards'
        }

        all_legends = []
        while True:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                all_legends.extend(data['data'])
            else:
                logging.error(f"Failed to fetch legendary creatures: {response.status_code}")
                break

            if not data.get('has_more'):
                break

            url = data['next_page']
            time.sleep(0.2)

        self._save_cache('legendary_creatures', all_legends)
        return all_legends
    
    def find_character_references(self, min_references=2):
        """Find all characters and their references."""
        legendary_cards = self.get_legendary_creatures()

        for card in legendary_cards:
            character_name = self.extract_character_name(card['name'])
            if len(character_name) < 3: # avoid false positives. necessary?
                continue

            references = self.search_for_character_references(character_name)
            if len(references) >= min_references:
                self.characters[character_name] = references
            sorted_characters = sorted(
                self.characters.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
        
        return sorted_characters


    def extract_character_name(self, card_name):
        """Extract the core character name from a card name."""
        if not hasattr(self, '_planeswalker_names'):
            self._planeswalker_names = self.get_planeswalker_full_names()

        # Remove stuff in parentheses, split on dual-faced cards
        name = re.sub(r'\([^)]*\)', '', card_name).split('//')[0].strip()

        # if ' and ' in name:
        #     # Store both names for cards like "X and Y"
        #     return [part.strip() for part in name.split(' and ')]
        
        # Split on common separators and take the first part
        for separator in [',', ' the ', ' of ', ' and ']:
            name = name.split(separator)[0]
            
        return name.strip()
    
    def search_for_character_references(self, character_name):
        """Search for cards that reference a character, using cache if available."""
        cache_key = f"references_{re.sub(r'[^\w]', '_', character_name.lower())}"
        cached_data = self._load_cache(cache_key)
        if cached_data is not None:
            logging.info(f"Using cached data for {character_name}")
            return set(cached_data)

        print(f"Searching Scryfall for {character_name}")
        url = f"{self.base_url}/cards/search"
        params = {
            # 'q': f'name:{character_name}', 
            'q': f'name:/^{re.escape(character_name)}\\b|\\b{re.escape(character_name)}$/',
            'unique': 'cards'
        }

        referenced_cards = set()
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                referenced_cards.update(
                    card['name'].split(' // ')[0].strip()
                    for card in data['data']
                    if 'Emblem' not in card['name']
                    # card['name'] for card in data['data']
                )


                url = data.get('next_page')
                params = None
            else:
                logging.error(f"Failed to fetch references for {character_name}: {response.status_code}")
                self._save_cache(cache_key, list(referenced_cards))
        except Exception as e:
            logging.error(f"Error searching for {character_name}: {e}")

        return referenced_cards
    
    def get_planeswalker_full_names(self):
        """Get full names of all planeswalkers from Scryfall."""
        cached_data = self._load_cache('planeswalker_names')
        if cached_data is not None:
            logging.info("Using cached planeswalker names")
            return set(cached_data)
        
        logging.info("Fetching planeswalker names from Scryfall...")
        url = f"{self.base_url}/cards/search"
        params = {
            'q': 'type:planeswalker',
            'unique': 'cards'
        }
        
        planeswalker_names = set()
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                for card in data['data']:
                    # Get the name before any special characters
                    full_name = card['name'].split('//')[0].strip()
                    # Remove any text in parentheses
                    full_name = re.sub(r'\([^)]*\)', '', full_name).strip()
                    # Remove titles after commas
                    full_name = full_name.split(',')[0].strip()
                    planeswalker_names.add(full_name)
                    
                while data.get('has_more'):
                    time.sleep(0.2)
                    response = requests.get(data['next_page'])
                    if response.status_code == 200:
                        data = response.json()
                        for card in data['data']:
                            full_name = card['name'].split('//')[0].strip()
                            full_name = re.sub(r'\([^)]*\)', '', full_name).strip()
                            full_name = full_name.split(',')[0].strip()
                            planeswalker_names.add(full_name)

                self._save_cache('planeswalker_names', list(planeswalker_names))
        except Exception as e:
            logging.error(f"Error fetching planeswalker names: {e}")
        
        return planeswalker_names

def main():
    finder = MTGCharacterFinder()
    characters = finder.find_character_references()

    print("\nCharacters with multiple card references:")
    print("----------------------------------------")
    for character, cards in characters:
        print(f"\n{character} ({len(cards)} cards):")
        for card in sorted(cards):
            print(f"  - {card}")

if __name__ == "__main__":
    main()