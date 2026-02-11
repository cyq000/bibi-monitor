"""US3 - 可配置监控阈值与时间窗口 的单元测试"""
import pytest
import json
import tempfile
from pathlib import Path
from src.config_manager import ConfigManager, ThresholdConfig


class TestThresholdConfig:
    """阈值配置模型测试"""

    def test_default_threshold_config(self):
        """测试默认阈值配置"""
        config = ThresholdConfig()
        
        assert config.score_threshold == 2.0
        assert config.volume_min == 10_000_000
        assert config.volume_max == 80_000_000
        print("✅ 默认阈值配置正确")

    def test_custom_threshold_config(self):
        """测试自定义阈值配置"""
        config = ThresholdConfig(
            score_threshold=3.5,
            volume_min=5_000_000,
            volume_max=50_000_000,
        )
        
        assert config.score_threshold == 3.5
        assert config.volume_min == 5_000_000
        assert config.volume_max == 50_000_000
        print("✅ 自定义阈值配置正确")

    def test_threshold_validation(self):
        """测试阈值验证"""
        # 有效配置
        config = ThresholdConfig(
            score_threshold=2.5,
            volume_min=10_000_000,
            volume_max=80_000_000,
        )
        assert config.validate() is True
        print("✅ 有效配置验证通过")

        # 无效配置：min >= max
        with pytest.raises(ValueError):
            ThresholdConfig(
                score_threshold=2.0,
                volume_min=100_000_000,
                volume_max=50_000_000,
            ).validate()
        print("✅ 无效配置验证失败（如预期）")

    def test_threshold_bounds(self):
        """测试阈值边界"""
        # 最小值
        config_min = ThresholdConfig(
            score_threshold=0.1,
            volume_min=100_000,
            volume_max=1_000_000,
        )
        assert config_min.score_threshold == 0.1
        print("✅ 最小阈值边界正确")

        # 最大值
        config_max = ThresholdConfig(
            score_threshold=100.0,
            volume_min=1_000_000_000,
            volume_max=10_000_000_000,
        )
        assert config_max.score_threshold == 100.0
        print("✅ 最大阈值边界正确")


class TestConfigManager:
    """配置管理器测试"""

    @pytest.fixture
    def temp_config_file(self):
        """临时配置文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 暂时覆盖配置文件路径
            ConfigManager.CONFIG_FILE = Path(tmpdir) / "test_config.json"
            yield tmpdir
            # 清理
            if ConfigManager.CONFIG_FILE.exists():
                ConfigManager.CONFIG_FILE.unlink()

    def test_config_manager_defaults(self, temp_config_file):
        """测试配置管理器默认值"""
        cfg = ConfigManager()
        
        defaults = cfg.show()
        assert defaults["score_threshold"] == 2.0
        assert defaults["volume_min"] == 10_000_000
        assert defaults["volume_max"] == 80_000_000
        print("✅ 配置管理器默认值正确")

    def test_config_set_and_get(self, temp_config_file):
        """测试设置和获取配置"""
        cfg = ConfigManager()
        
        # 设置单个值
        assert cfg.set("score_threshold", 2.5) is True
        assert cfg.get("score_threshold") == 2.5
        print("✅ 设置和获取配置正确")

        # 设置多个值
        assert cfg.set("volume_min", 5_000_000) is True
        assert cfg.set("volume_max", 100_000_000) is True
        assert cfg.get("volume_min") == 5_000_000
        assert cfg.get("volume_max") == 100_000_000
        print("✅ 批量设置配置正确")

    def test_config_validation(self, temp_config_file):
        """测试配置验证"""
        cfg = ConfigManager()
        
        # 设置无效值（volume_min >= volume_max）
        assert cfg.set("volume_min", 100_000_000) is True
        assert cfg.set("volume_max", 50_000_000) is False  # 应该失败
        print("✅ 配置验证失败（如预期）")

    def test_per_symbol_thresholds(self, temp_config_file):
        """测试按币种的独立阈值"""
        cfg = ConfigManager()
        
        # 为 BTCUSDT 设置专用阈值
        assert cfg.set_symbol_threshold("BTCUSDT", score_threshold=3.0, volume_min=5_000_000) is True
        
        # 获取 BTCUSDT 的阈值
        btc_threshold = cfg.get_threshold_for_symbol("BTCUSDT")
        assert btc_threshold.score_threshold == 3.0
        assert btc_threshold.volume_min == 5_000_000
        print("✅ 币种专用阈值设置成功")

        # 获取未配置币种的阈值（应返回全局默认值）
        eth_threshold = cfg.get_threshold_for_symbol("ETHUSDT")
        assert eth_threshold.score_threshold == 2.0  # 全局默认值
        print("✅ 未配置币种返回全局默认值")

    def test_config_save_and_load(self, temp_config_file):
        """测试配置保存和加载"""
        cfg1 = ConfigManager()
        cfg1.set("score_threshold", 2.5)
        cfg1.set_symbol_threshold("BTCUSDT", score_threshold=3.0)
        assert cfg1.save() is True
        print("✅ 配置保存成功")

        # 创建新实例，应该加载之前保存的配置
        cfg2 = ConfigManager()
        assert cfg2.get("score_threshold") == 2.5
        
        btc_threshold = cfg2.get_threshold_for_symbol("BTCUSDT")
        assert btc_threshold.score_threshold == 3.0
        print("✅ 配置加载成功")

    def test_config_reset(self, temp_config_file):
        """测试配置重置"""
        cfg = ConfigManager()
        
        # 修改配置
        cfg.set("score_threshold", 5.0)
        assert cfg.get("score_threshold") == 5.0
        
        # 重置配置
        assert cfg.reset() is True
        assert cfg.get("score_threshold") == 2.0  # 恢复默认值
        print("✅ 配置重置成功")

    def test_config_file_format(self, temp_config_file):
        """测试配置文件格式"""
        cfg = ConfigManager()
        cfg.set("score_threshold", 2.5)
        cfg.set_symbol_threshold("BTCUSDT", score_threshold=3.0)
        cfg.save()

        # 检查文件内容
        with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "score_threshold" in data
        assert "per_symbol_thresholds" in data
        assert "_metadata" in data
        assert "saved_at" in data["_metadata"]
        print("✅ 配置文件格式正确")


class TestConfigAPI:
    """配置 API 端点测试"""

    @pytest.mark.asyncio
    async def test_api_get_config(self):
        """测试 GET /config 端点"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
            
            client = TestClient(app)
            response = client.get("/config")
            
            assert response.status_code == 200
            config = response.json()
            assert "score_threshold" in config
            assert "volume_min" in config
            assert "volume_max" in config
            print(f"✅ API GET /config: {config}")
        except ImportError:
            pytest.skip("FastAPI 未安装")

    @pytest.mark.asyncio
    async def test_api_update_config(self):
        """测试 POST /config 端点"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
            
            client = TestClient(app)
            response = client.post(
                "/config",
                params={
                    "score_threshold": 2.5,
                    "volume_min": 5_000_000,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["config"]["score_threshold"] == 2.5
            print("✅ API POST /config 成功")
        except ImportError:
            pytest.skip("FastAPI 未安装")

    @pytest.mark.asyncio
    async def test_api_symbol_config(self):
        """测试币种配置 API"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
            
            client = TestClient(app)
            
            # 设置币种配置
            response = client.post(
                "/config/symbol/BTCUSDT",
                params={"score_threshold": 3.0}
            )
            assert response.status_code == 200
            
            # 获取币种配置
            response = client.get("/config/symbol/BTCUSDT")
            assert response.status_code == 200
            config = response.json()
            assert config["symbol"] == "BTCUSDT"
            print("✅ API 币种配置端点正确")
        except ImportError:
            pytest.skip("FastAPI 未安装")

    @pytest.mark.asyncio
    async def test_api_reset_config(self):
        """测试重置配置 API"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
            
            client = TestClient(app)
            response = client.post("/config/reset")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            print("✅ API POST /config/reset 成功")
        except ImportError:
            pytest.skip("FastAPI 未安装")


class TestConfigIntegration:
    """集成测试"""

    def test_multiple_symbol_configs(self):
        """测试多币种配置"""
        cfg = ConfigManager()
        
        # 为不同币种设置不同阈值
        cfg.set_symbol_threshold("BTCUSDT", score_threshold=3.0, volume_min=20_000_000)
        cfg.set_symbol_threshold("ETHUSDT", score_threshold=2.5, volume_min=10_000_000)
        cfg.set_symbol_threshold("ADAUSDT", score_threshold=2.0, volume_min=5_000_000)
        
        # 验证配置
        btc = cfg.get_threshold_for_symbol("BTCUSDT")
        eth = cfg.get_threshold_for_symbol("ETHUSDT")
        ada = cfg.get_threshold_for_symbol("ADAUSDT")
        
        assert btc.score_threshold == 3.0
        assert eth.score_threshold == 2.5
        assert ada.score_threshold == 2.0
        print("✅ 多币种独立配置正确")

    def test_config_override_global(self):
        """测试币种配置覆盖全局配置"""
        cfg = ConfigManager()
        
        # 设置全局配置
        cfg.set("score_threshold", 2.0)
        cfg.set("volume_min", 10_000_000)
        
        # 为 BTCUSDT 设置高于全局的阈值
        cfg.set_symbol_threshold("BTCUSDT", score_threshold=5.0)
        
        # 验证全局和币种配置不同
        global_threshold = cfg.get_threshold_for_symbol("NONEXISTENT")
        btc_threshold = cfg.get_threshold_for_symbol("BTCUSDT")
        
        assert global_threshold.score_threshold == 2.0
        assert btc_threshold.score_threshold == 5.0
        print("✅ 币种配置正确覆盖全局配置")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
