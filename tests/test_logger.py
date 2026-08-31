import os
import shutil
import tempfile
import unittest
import logging
from pathlib import Path

from src.utils.logger import setup_logging, get_logger


class TestLogger(unittest.TestCase):
    """Testes unitários para o sistema de logging centralizado do Medusa VTT."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test_logs", "medusa.log")

    def tearDown(self):
        # Remove handlers antes de deletar diretório temporário
        root = logging.getLogger()
        for h in list(root.handlers):
            h.close()
            root.removeHandler(h)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_setup_logging_creates_file_and_logs_messages(self):
        setup_logging(level=logging.INFO, log_file=self.log_file)
        logger = get_logger("TestModule")

        msg = "Teste de log com acentuação: Ação e Coração 🐉"
        logger.info(msg)

        self.assertTrue(os.path.isfile(self.log_file))

        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[INFO]", content)
        self.assertIn("[TestModule]", content)
        self.assertIn(msg, content)

    def test_setup_logging_debug_flag(self):
        setup_logging(log_file=self.log_file, debug=True)
        logger = get_logger("DebugModule")

        debug_msg = "Mensagem de depuração DEBUG"
        logger.debug(debug_msg)

        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[DEBUG]", content)
        self.assertIn(debug_msg, content)


if __name__ == "__main__":
    unittest.main()
