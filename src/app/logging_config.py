import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(app=None, log_dir: str = "logs"):
    """
    Configura logging para a aplicação Flask
    """
    # Criar diretório de logs se não existir
    os.makedirs(log_dir, exist_ok=True)

    # Criar formatador
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Handler para arquivo (todos os logs)
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Loggers específicos
    loggers_to_config = [
        'flask',
        'flask_cors',
        'app',
        'instagram',
        'media_cache',
        'warmup',
        'cache'
    ]

    for logger_name in loggers_to_config:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

    if app:
        app.logger.info("Logging configurado com sucesso")

    return root_logger