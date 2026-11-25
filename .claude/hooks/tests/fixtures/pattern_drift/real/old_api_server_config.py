import sys

from loguru import logger

# Logger
# Here, we incorporate {process} into the default format
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> |<red> PID {process}</red> | <level>{level: <8}</level>| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# SLURM config
SLURM_CONFIG = {
    "--nodes": 1,
    "--ntasks": 1,
    "--cpus-per-task": 2,
    "--mem-per-cpu": "42024M",
    "--mail-type": "END",
}
