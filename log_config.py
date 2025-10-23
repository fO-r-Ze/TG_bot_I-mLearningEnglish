import logging

LOG_FILE_NAME = 'user_logs.log'
FORMATTER = '%(asctime)s | %(levelname)-8s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

logger = logging.getLogger(__name__)
handler = logging.FileHandler(LOG_FILE_NAME, mode='a', encoding='utf-8')
formatter = logging.Formatter(FORMATTER, DATE_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)