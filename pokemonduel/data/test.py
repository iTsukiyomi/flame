import os
import requests
import json

# Load your Pokemon data from pfile.json
with open('pfile.json', 'r') as file:
    pokemon_data = json.load(file)


# Create 'img' folder if it doesn't exist
def make_img_folder():
    if not os.path.exists('img'):
        os.makedirs('img')
        print("Created 'img' folder")


# Function to get the front sprite URL from PokeAPI
def get_sprite_url(identifier):
    url = f'https://pokeapi.co/api/v2/pokemon/{identifier}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['sprites']['front_default']
        else:
            return None
    except requests.exceptions.RequestException:
        return None


# Download the sprite by URL and save with the Pokemon's ID as the filename
def download_sprite(sprite_url, poke_id):
    if sprite_url is None:
        print(f"No sprite URL for ID {poke_id}, skipping.")
        return

    try:
        response = requests.get(sprite_url)
        if response.status_code == 200:
            file_path = f"img/{poke_id}.png"
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded sprite for ID {poke_id}")
        else:
            print(f"Failed to download sprite for ID {poke_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading sprite for ID {poke_id}: {e}")


# Main execution
make_img_folder()

# Go through each Pokemon, fetch sprite URLs, and download the sprites
for pokemon in pokemon_data:
    sprite_url = get_sprite_url(pokemon['identifier'])
    download_sprite(sprite_url, pokemon['id'])

print("All sprites downloaded successfully!")
