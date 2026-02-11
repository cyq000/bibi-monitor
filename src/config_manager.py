"""配置管理系统：支持动态修改监控阈值

支持以下配置参数：
- score_threshold: 买卖比率阈值（默认 2.0）
- volume_min: 24h 最小体积 USDT（默认 10M）
- volume_max: 24h 最大体积 USDT（默认 80M）
- per_symbol_thresholds: 按币种的独立阈值（可选）
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from src.logging import get_logger

logger = get_logger(__name__)


class ThresholdConfig(BaseModel):
    """单个阈值配置"""
    score_threshold: float = Field(default=2.0, ge=0.1, le=100.0, description="最小买卖比率")
    volume_min: int = Field(default=10_000_000, ge=100_000, description="最小 24h 体积 USDT")
    volume_max: int = Field(default=80_000_000, ge=1_000_000, description="最大 24h 体积 USDT")

    def validate(self) -> bool:
        """验证配置的有效性"""
        if self.volume_min >= self.volume_max:
            raise ValueError(f"volume_min ({self.volume_min}) 必须小于 volume_max ({self.volume_max})")
        return True


class ConfigManager:
    """配置管理器：支持文件和环境变量配置"""

    # 默认配置
    DEFAULT_CONFIG = {
        "score_threshold": 2.0,
        "volume_min": 10_000_000,
        "volume_max": 80_000_000,
        "per_symbol_thresholds": {},  # 按币种的独立阈值
        # 币种发现相关配置
        "enable_discovery": True,
        "discovery_interval_seconds": 86400,  # 24小时发现一次
        "discovery_excluded_symbols": [],  # 排除列表
        "discovery_max_symbols": None,  # 最多监控多少个币种（None=不限制）
    }

    # 配置文件路径
    CONFIG_FILE = Path(".") / "monitor_config.json"

    def __init__(self):
        """初始化配置管理器"""
        self._config = self.DEFAULT_CONFIG.copy()
        self._load_from_file()
        self._load_from_env()
        logger.info(f"配置已加载：score_threshold={self._config['score_threshold']}, "
                   f"volume=[{self._config['volume_min']:,}, {self._config['volume_max']:,}]")

    def _load_from_file(self) -> None:
        """从配置文件加载"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
                    logger.info(f"从文件加载配置：{self.CONFIG_FILE}")
            except Exception as e:
                logger.warning(f"加载配置文件失败：{e}，使用默认配置")

    def _load_from_env(self) -> None:
        """从环境变量加载（优先级最高）"""
        env_mappings = {
            "SCORE_THRESHOLD": ("score_threshold", float),
            "VOLUME_MIN": ("volume_min", int),
            "VOLUME_MAX": ("volume_max", int),
        }

        for env_var, (config_key, type_func) in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                try:
                    self._config[config_key] = type_func(value)
                    logger.info(f"从环境变量加载 {env_var}: {value}")
                except ValueError as e:
                    logger.warning(f"环境变量 {env_var} 格式错误：{e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def get_threshold_for_symbol(self, symbol: str) -> ThresholdConfig:
        """获取指定币种的阈值配置"""
        per_symbol = self._config.get("per_symbol_thresholds", {})

        if symbol in per_symbol:
            # 使用币种专用配置
            symbol_config = per_symbol[symbol]
            return ThresholdConfig(
                score_threshold=symbol_config.get("score_threshold", self._config["score_threshold"]),
                volume_min=symbol_config.get("volume_min", self._config["volume_min"]),
                volume_max=symbol_config.get("volume_max", self._config["volume_max"]),
            )

        # 使用全局配置
        return ThresholdConfig(
            score_threshold=self._config["score_threshold"],
            volume_min=self._config["volume_min"],
            volume_max=self._config["volume_max"],
        )

    def set(self, key: str, value: Any) -> bool:
        """设置配置值"""
        old_value = self._config.get(key)

        # 验证阈值配置
        if key in ["score_threshold", "volume_min", "volume_max"]:
            temp_config = self._config.copy()
            temp_config[key] = value
            try:
                ThresholdConfig(
                    score_threshold=temp_config["score_threshold"],
                    volume_min=temp_config["volume_min"],
                    volume_max=temp_config["volume_max"],
                ).validate()
            except ValueError as e:
                logger.error(f"配置验证失败：{e}")
                return False

        self._config[key] = value
        logger.info(f"配置已更新：{key} = {old_value} → {value}")
        return True

    def set_symbol_threshold(self, symbol: str, **kwargs) -> bool:
        """为特定币种设置阈值"""
        if "per_symbol_thresholds" not in self._config:
            self._config["per_symbol_thresholds"] = {}

        if symbol not in self._config["per_symbol_thresholds"]:
            self._config["per_symbol_thresholds"][symbol] = {}

        symbol_config = self._config["per_symbol_thresholds"][symbol]

        for key, value in kwargs.items():
            if key in ["score_threshold", "volume_min", "volume_max"]:
                symbol_config[key] = value
                logger.info(f"币种 {symbol} 阈值已更新：{key} = {value}")

        return True

    def save(self) -> bool:
        """保存配置到文件"""
        try:
            # 添加元数据
            config_to_save = self._config.copy()
            config_to_save["_metadata"] = {
                "saved_at": datetime.utcnow().isoformat(),
                "version": "0.1.0",
            }

            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, ensure_ascii=False, indent=2)

            logger.info(f"配置已保存到：{self.CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败：{e}")
            return False

    def reset(self) -> bool:
        """重置为默认配置"""
        self._config = self.DEFAULT_CONFIG.copy()
        logger.info("配置已重置为默认值")
        return self.save()

    def show(self) -> Dict:
        """获取配置概览"""
        return {
            "score_threshold": self._config["score_threshold"],
            "volume_min": self._config["volume_min"],
            "volume_max": self._config["volume_max"],
            "per_symbol_thresholds": self._config.get("per_symbol_thresholds", {}),
        }


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    return config_manager


if __name__ == "__main__":
    # 示例用法
    cfg = config_manager
    
    print("当前配置：")
    print(json.dumps(cfg.show(), ensure_ascii=False, indent=2))
    print()
    
    # 查看特定币种的阈值
    btc_threshold = cfg.get_threshold_for_symbol("BTCUSDT")
    print(f"BTCUSDT 的阈值：")
    print(f"  score_threshold: {btc_threshold.score_threshold}")
    print(f"  volume_min: {btc_threshold.volume_min:,}")
    print(f"  volume_max: {btc_threshold.volume_max:,}")
