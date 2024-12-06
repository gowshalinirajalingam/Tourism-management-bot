import subprocess
from dotenv import load_dotenv
import os 
load_dotenv()


WHAT_TOKEN = "EAAOXhdmUSwoBO0xsTny64TmlGg5Gb4EyLMovKZCshCeeVtbx3tJPalK1HNiOAzZBkyvCUZArr4N57F1WNklfjMGAar5Fceo1RyJK9GZCLZCCSwdajQNaAlvnZAPtBP7xKQmZBzLxvRGaVeZBKxjZCAxFW3yZCPcl1tg5DsmfhxXwyHycLiZALZBQbcu12i8RpvrgSqCHNISIW0bHDeXU1zTq5ZCXl"
VERSION = os.getenv("VERSION")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Define the curl command
curl_command = [
    "curl",
    "-X", "POST",  # Change to the desired HTTP method
    "https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/media",  # Replace with your URL
    "-H", "Authorization: Bearer {WHAT_TOKEN}"  # Replace with your headers
    "-F", "file=@\"00000104-Sedan Car Types.pdf\""  # Replace with your headers
    "-F", "type= pdf"  # Replace with your headers
    "-F", "messaging_product=\"whatsapp\""  # Replace with your headers


]

# Execute the curl command
result = subprocess.run(curl_command, capture_output=True, text=True)

# Print the output and error (if any)
print("Output:", result.stdout)
print("Error:", result.stderr)