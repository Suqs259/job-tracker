import sys
from pathlib import Path

import pytest

# 让测试可以直接 import 项目根目录的 app 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """每个测试用独立的临时数据库，避免相互污染。"""
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        "SECRET_KEY": "test-secret",
        "TIMEZONE": "Asia/Shanghai",
        "PAGE_SIZE_DEFAULT": 5,
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """注册并登录（注册接口会自动建立会话）。"""
    response = client.post(
        "/api/auth/register",
        json={"username": "tester", "password": "secret123"},
    )
    assert response.status_code == 201
    return client
