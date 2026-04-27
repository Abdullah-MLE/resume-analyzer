import logging
import os

# Create a logger
logger = logging.getLogger("scraper_system")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File Handler (Writes everything INFO and above to scraper.log)
file_handler = logging.FileHandler('scraper.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Console Handler (Only writes WARNING and ERROR to the terminal to avoid spam)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)

# Prevent duplicate logs if module is reloaded
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def get_logger():
    return logger
