import logging

logging.basicConfig(
    # filename='logs/log_file_name.log',
    level=logging.DEBUG,
    format='[%(asctime)s] %(filename)-28s:%(lineno)-4d %(levelname)-7s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


__all__ = [
    "logger",
]
