import logging
from typing import Optional


def setup_logging(level: int = logging.INFO, log_format: Optional[str] = None) -> None:
    """
    Configura o sistema de logs centralizado do Medusa VTT.
    Formato padrão: [%(asctime)s] [%(levelname)s] %(name)s: %(message)s
    """
    fmt = log_format or "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado para o módulo especificado."""
    return logging.getLogger(name)
