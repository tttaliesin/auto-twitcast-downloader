"""설정 관리 모듈"""

import json
from pathlib import Path
from typing import Any


class ConfigManager:
    """설정 파일 관리 클래스"""

    def __init__(self, config_file: str = "config.json"):
        """
        Args:
            config_file: 설정 파일 이름 (기본값: config.json)
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """설정 파일을 불러옵니다."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_config(self) -> bool:
        """설정 파일을 저장합니다."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """설정 값을 가져옵니다."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """설정 값을 저장합니다."""
        self.config[key] = value

    def get_all(self) -> dict:
        """모든 설정을 가져옵니다."""
        return self.config.copy()

    def update(self, data: dict):
        """여러 설정을 한 번에 업데이트합니다."""
        self.config.update(data)