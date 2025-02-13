import logging
import sys
from logging import handlers


log_file = '../logs/print_jobs.log'

logger = logging.getLogger('print_jobs')
logger.setLevel(logging.DEBUG)

log_format = logging.Formatter("%(asctime)s [%(levelname)-5.5s ] %(message)s")

file_handler = handlers.RotatingFileHandler(log_file, maxBytes=10000000, backupCount=10)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)

logger.addHandler(file_handler)
logger.addHandler(console_handler)