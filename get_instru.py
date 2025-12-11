import requests
import os

# Desktop path (Windows)
desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

# File name
file_path = os.path.join(desktop, "zerodha_instruments.csv")

# Instruments URL
url = "https://api.kite.trade/instruments"

print("Downloading Zerodha instruments file...")

response = requests.get(url)

if response.status_code == 200:
    with open(file_path, "wb") as f:
        f.write(response.content)
    print("Download complete!")
    print("File saved to:", file_path)
else:
    print("Failed to download:", response.status_code)
