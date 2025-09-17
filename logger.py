import logging

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("karlo_update.log"),  # log ke file
        logging.StreamHandler()  # opsional: log ke console juga
    ]
)

logger = logging.getLogger(__name__)
