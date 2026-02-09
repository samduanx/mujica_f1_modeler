import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def get_race_names():
    """Return the list of 2022 F1 Grand Prix races."""
    return [
        "bahrain", "saudi-arabian", "australian", "emilia-romagna", 
        "miami", "spanish", "monaco", "azerbaijan", "canadian", 
        "british", "austrian", "french", "hungarian", "belgian", 
        "dutch", "italian", "russian", "singapore", "japanese", 
        "united-states", "mexico", "brazil", "abu-dhabi"
    ]

def generate_url_candidates(race_name):
    """Generate possible URL patterns for a given race."""
    base = "https://press.pirelli.com/"
    patterns = [
        f"2022-{race_name}-grand-prix--preview/",
        f"2022-{race_name}-grand-prix---preview/",
        f"2022-{race_name}-grand-prix---preview-0/",
        f"2022-{race_name}-grand-prix-preview/"
    ]
    return [urljoin(base, pattern) for pattern in patterns]

def find_valid_url(race_name):
    """Find the correct URL pattern that returns a 200 status code."""
    for url in generate_url_candidates(race_name):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"Found valid URL: {url}")
                return url
        except requests.exceptions.RequestException:
            continue
    return None

def download_images(url, output_dir):
    """Download all images from a valid preview page."""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Create race-specific subdirectory
        race_name = re.search(r'2022-(.*?)-grand-prix', url).group(1)
        race_dir = os.path.join(output_dir, race_name)
        os.makedirs(race_dir, exist_ok=True)

        # Find all image tags
        img_tags = soup.find_all('img')
        downloaded = 0

        for img in img_tags:
            img_url = img.get('src')

            # Skip if no src attribute or it's a data URL
            if not img_url or img_url.startswith('data:'):
                continue

            # Handle relative URLs
            if not img_url.startswith(('http://', 'https://')):
                img_url = urljoin(url, img_url)

            # Skip non-image URLs
            if not any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                continue

            # Create filename from URL
            filename = os.path.basename(img_url.split('?')[0])
            filepath = os.path.join(race_dir, filename)

            # Download the image
            try:
                img_data = requests.get(img_url, timeout=10).content
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                downloaded += 1
                print(f"Downloaded: {filename} to {race_dir}")
            except Exception as e:
                print(f"Failed to download {img_url}: {str(e)}")

        return downloaded
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        return 0

def main():
    # Create output directory
    output_dir = "pirelli_2022_f1_images"
    os.makedirs(output_dir, exist_ok=True)

    race_names = get_race_names()
    total_images = 0

    print("Starting to download Pirelli 2022 F1 Grand Prix preview images...")
    print(f"Found {len(race_names)} races in the 2022 calendar.【1】")

    for race_name in race_names:
        print(f"\nProcessing {race_name.replace('-', ' ').title()} Grand Prix...")

        valid_url = find_valid_url(race_name)
        if valid_url:
            count = download_images(valid_url, output_dir)
            total_images += count
            # Be respectful with requests
            time.sleep(1)
        else:
            print(f"No valid URL found for {race_name} Grand Prix")

    print(f"\nProcess completed! Downloaded {total_images} images across {len(race_names)} races.")
    print(f"Images saved to: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    main()
