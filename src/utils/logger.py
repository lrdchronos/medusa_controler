import logging
import os
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = "logs/medusa.log",
    log_format: Optional[str] = None,
    debug: bool = False,
) -> None:
    """
    Configura o sistema de logs centralizado do Medusa VTT.
    Mantém a saída formatada no terminal (Console Handler) e adiciona
    um FileHandler com encoding UTF-8 gravando em logs/medusa.log.

    Formato padrão: [%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s
    """
    if debug:
        level = logging.DEBUG

    fmt = log_format or "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
    formatter = logging.Formatter(fmt)

    # Configuração dos Handlers
    handlers: list[logging.Handler] = []

    # 1. Console Handler (Terminal)
    # Reconfigura stdout se possível ou cria stream handler seguro
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # 2. File Handler (Arquivo em logs/medusa.log com UTF-8)
    if log_file:
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = Path.cwd() / log_path

        # Garante a criação do diretório se não existir
        log_dir = log_path.parent
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,  # 5 MB por arquivo de log
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configura o root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Limpa handlers pré-existentes para evitar duplicações
    for existing_h in list(root_logger.handlers):
        root_logger.removeHandler(existing_h)

    for h in handlers:
        root_logger.addHandler(h)


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado para o módulo especificado."""
    return logging.getLogger(name)

