#!/usr/bin/env python3
"""Command line interface for Paradox Mod Translator."""

import argparse
import os
import sys
from typing import List

from config.config_manager import ConfigManager
from utils.logging_utils import setup_logging, ApplicationLogger, create_session_log_file
from core.translation_workflow import TranslationWorkflow


class CLIApp:
    """Minimal application object used by TranslationWorkflow."""

    def __init__(self, config_file: str):
        self.config_manager = ConfigManager(config_file)
        log_file = create_session_log_file()
        setup_logging(log_file=log_file)
        self.logger = ApplicationLogger()
        # 禁用评审以避免交互
        self.config_manager.set_setting("auto_review_mode", False)

    def log_message(self, message: str, level: str = "info") -> None:
        self.logger.log_message(message, level)

    # TranslationWorkflow 会在评审模式下调用以下方法
    def review_translation(self, key_name: str, original_text: str, ai_translation: str, completion_callback) -> None:
        """Automatically confirm translation in CLI mode."""
        self.log_message(f"Review skipped for {key_name}", "debug")
        completion_callback(key_name, {"action": "confirm", "translation": ai_translation})

    def handle_review_completion(self, key_name: str, result: dict) -> None:
        self.log_message(f"Review completed for {key_name}: {result.get('action')}", "debug")


def discover_yml_files(path: str) -> List[str]:
    """Collect YML files from a file or directory."""
    if os.path.isfile(path):
        return [path]

    files = []
    for root, _, filenames in os.walk(path):
        for name in filenames:
            if name.lower().endswith(".yml"):
                files.append(os.path.join(root, name))
    return files


def run_cli(args: argparse.Namespace) -> int:
    app = CLIApp(args.config)

    source_lang = args.source or app.config_manager.get_setting("source_language")
    target_lang = args.target or app.config_manager.get_setting("target_language")
    style = args.style or app.config_manager.get_setting("game_mod_style")
    model = args.model or app.config_manager.get_setting("selected_model")

    workflow = TranslationWorkflow(app, app.config_manager)

    def progress_callback(done: int, total: int) -> None:
        percent = (done / total * 100) if total else 0
        app.log_message(f"Progress: {done}/{total} ({percent:.1f}%)", "info")

    workflow.set_progress_callback(progress_callback)

    source_files = discover_yml_files(args.path)
    if not source_files:
        app.log_message("No YML files found", "error")
        return 1

    valid, message = workflow.validate_prerequisites(source_lang, target_lang, source_files)
    if not valid:
        app.log_message(message, "error")
        return 1

    success = workflow.execute_translation(source_files, source_lang, target_lang, style, model)
    return 0 if success else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Paradox Mod Translator CLI")
    parser.add_argument("path", help="File or directory to translate")
    parser.add_argument("-s", "--source", help="Source language code")
    parser.add_argument("-t", "--target", help="Target language code")
    parser.add_argument("--style", help="Game or mod style prompt")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--config", default="translator_config.json", help="Config file path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.exit(run_cli(args))


if __name__ == "__main__":
    main()
