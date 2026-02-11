"""US2 - 查看与导出监控日志 的单元测试"""
import json
import csv
import io
from datetime import datetime, timedelta
import pytest
import tempfile
from pathlib import Path

from src.db import init_db, get_engine
from src.storage import storage
from src.cli_export import NotificationExporter
from sqlalchemy.orm import sessionmaker
from src.models import Notification, WindowMetric, Symbol


@pytest.fixture(autouse=True)
def setup_db():
    """初始化测试数据库"""
    init_db()
    yield
    # Teardown if needed


@pytest.fixture
def sample_data():
    """创建示例通知数据"""
    # 创建币种
    btc = storage.get_or_create_symbol("BTCUSDT", "BTC", "USDT", "PERPETUAL")
    eth = storage.get_or_create_symbol("ETHUSDT", "ETH", "USDT", "PERPETUAL")

    # 创建窗口指标
    for i in range(5):
        window_end = datetime.utcnow() - timedelta(hours=i)
        window_start = window_end - timedelta(hours=1)
        
        wm = storage.store_window_metric(
            symbol="BTCUSDT",
            window_type="1h",
            window_start=window_start,
            window_end=window_end,
            buy_taker_volume=50_000_000 + i * 1_000_000,
            sell_taker_volume=10_000_000 + i * 500_000,
            total_volume=60_000_000,
            score_a=4.0 + i * 0.1,
            volume_24h_usdt=40_000_000,
        )

        # 创建通知
        event_id = f"BTCUSDT-{window_start.isoformat()}-1h"
        payload = {
            "symbol": "BTCUSDT",
            "score": 4.0 + i * 0.1,
            "buy": 50_000_000,
        }
        storage.create_notification("BTCUSDT", wm.id, event_id, payload)

    # 创建另一个币种的通知
    for i in range(3):
        window_end = datetime.utcnow() - timedelta(hours=i)
        window_start = window_end - timedelta(hours=1)
        
        wm = storage.store_window_metric(
            symbol="ETHUSDT",
            window_type="1h",
            window_start=window_start,
            window_end=window_end,
            buy_taker_volume=30_000_000,
            sell_taker_volume=5_000_000,
            total_volume=35_000_000,
            score_a=6.0,
            volume_24h_usdt=25_000_000,
        )

        event_id = f"ETHUSDT-{window_start.isoformat()}-1h"
        payload = {"symbol": "ETHUSDT", "score": 6.0}
        storage.create_notification("ETHUSDT", wm.id, event_id, payload)

    return {"btc": btc, "eth": eth}


class TestExportCLI:
    """CLI 导出工具测试"""

    def test_query_all_notifications(self, sample_data):
        """测试查询所有通知"""
        exporter = NotificationExporter()
        records = exporter.query_notifications(days=30)
        
        assert len(records) == 8  # 5 BTCUSDT + 3 ETHUSDT
        print(f"✅ 查询到 {len(records)} 条通知")

    def test_query_by_symbol(self, sample_data):
        """测试按币种过滤"""
        exporter = NotificationExporter()
        records = exporter.query_notifications(days=30, symbol="BTCUSDT")
        
        assert len(records) == 5
        assert all(r["symbol"] == "BTCUSDT" for r in records)
        print(f"✅ BTCUSDT 通知数: {len(records)}")

    def test_query_nonexistent_symbol(self, sample_data):
        """测试查询不存在的币种"""
        exporter = NotificationExporter()
        records = exporter.query_notifications(days=30, symbol="NONEXISTENT")
        
        assert len(records) == 0
        print("✅ 不存在币种返回空结果")

    def test_export_json(self, sample_data):
        """测试 JSON 导出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.json"
            exporter = NotificationExporter()
            
            success = exporter.export_json(str(output_file), days=30)
            assert success
            assert output_file.exists()
            
            # 验证文件内容
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert "metadata" in data
            assert "records" in data
            assert data["metadata"]["record_count"] == 8
            assert len(data["records"]) == 8
            print(f"✅ JSON 导出: {len(data['records'])} 条记录")

    def test_export_csv(self, sample_data):
        """测试 CSV 导出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"
            exporter = NotificationExporter()
            
            success = exporter.export_csv(str(output_file), days=30)
            assert success
            assert output_file.exists()
            
            # 验证 CSV 内容
            with open(output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
            
            assert len(records) == 8
            assert "symbol" in records[0]
            assert "status" in records[0]
            print(f"✅ CSV 导出: {len(records)} 条记录")

    def test_export_filtered_json(self, sample_data):
        """测试带过滤的 JSON 导出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "btc.json"
            exporter = NotificationExporter()
            
            success = exporter.export_json(
                str(output_file),
                days=30,
                symbol="BTCUSDT",
            )
            assert success
            
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data["metadata"]["record_count"] == 5
            assert all(r["symbol"] == "BTCUSDT" for r in data["records"])
            print(f"✅ 按币种过滤 JSON 导出: {len(data['records'])} 条记录")


class TestExportAPI:
    """API 导出端点测试 (需要 FastAPI 和 TestClient)"""

    @pytest.mark.asyncio
    async def test_api_notifications_endpoint(self, sample_data):
        """测试 /notifications 端点"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
            
            client = TestClient(app)
            response = client.get("/notifications?days=30")
            
            assert response.status_code == 200
            data = response.json()
            assert "records" in data
            assert "total" in data
            assert data["total"] == 8
            print(f"✅ API /notifications: {data['total']} 条记录")
        except ImportError:
            pytest.skip("FastAPI 未安装")

    @pytest.mark.asyncio
    async def test_api_export_json(self, sample_data):
        """测试 /export 端点（JSON）"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
            
            client = TestClient(app)
            response = client.get("/export?days=30&format=json")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            
            # 解析返回的 JSON
            data = json.loads(response.content)
            assert len(data) > 0
            print(f"✅ API /export (json): {len(data)} 条记录")
        except ImportError:
            pytest.skip("FastAPI 未安装")

    @pytest.mark.asyncio
    async def test_api_stats(self, sample_data):
        """测试 /stats 统计端点"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
            
            client = TestClient(app)
            response = client.get("/stats?days=30")
            
            assert response.status_code == 200
            stats = response.json()
            assert "total_notifications" in stats
            assert "sent_count" in stats
            assert "symbols" in stats
            assert stats["total_notifications"] == 8
            print(f"✅ API /stats: total={stats['total_notifications']}")
        except ImportError:
            pytest.skip("FastAPI 未安装")


class TestExportDataIntegrity:
    """数据完整性测试"""

    def test_export_contains_all_fields(self, sample_data):
        """测试导出数据包含所有必要字段"""
        exporter = NotificationExporter()
        records = exporter.query_notifications(days=30)
        
        required_fields = [
            "id", "symbol", "event_id", "status",
            "attempts", "created_at", "sent_at"
        ]
        
        for record in records:
            for field in required_fields:
                assert field in record, f"缺少字段: {field}"
        
        print(f"✅ 导出数据包含所有必要字段")

    def test_export_numeric_precision(self, sample_data):
        """测试导出数据的数值精度"""
        exporter = NotificationExporter()
        records = exporter.query_notifications(
            days=30,
            symbol="BTCUSDT"
        )
        
        # 检查数值字段的精度
        for record in records:
            if "score_a" in record:
                assert isinstance(record["score_a"], float)
                assert 0 <= record["score_a"] <= 100
            
            if "buy_volume" in record:
                assert isinstance(record["buy_volume"], float)
                assert record["buy_volume"] > 0
        
        print(f"✅ 导出数据数值精度正确")

    def test_export_time_ordering(self, sample_data):
        """测试导出数据时间顺序"""
        exporter = NotificationExporter()
        records = exporter.query_notifications(days=30)
        
        times = [
            datetime.fromisoformat(r["created_at"])
            for r in records
            if r["created_at"]
        ]
        
        # 应该是倒序（最新的在前）
        for i in range(len(times) - 1):
            assert times[i] >= times[i + 1], "时间不是倒序"
        
        print(f"✅ 导出数据时间顺序正确（倒序）")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
