from datetime import datetime
from zoneinfo import ZoneInfo


def make_record(**overrides):
    payload = {
        "company": "示例科技",
        "position": "大数据开发",
        "city": "桂林",
        "channel": "官网",
        "salary": "8-12K",
        "apply_date": "2026-11-10",
        "status": "已投递",
        "jd_url": "https://example.com/jd",
        "note": "",
    }
    payload.update(overrides)
    return payload


def create(client, **overrides):
    response = client.post("/api/applications", json=make_record(**overrides))
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_returns_record(auth_client):
    record = create(auth_client)
    assert record["id"] > 0
    assert record["company"] == "示例科技"
    assert record["created_at"] == record["updated_at"]


def test_create_requires_company(auth_client):
    response = auth_client.post("/api/applications", json={"position": "开发", "apply_date": "2026-11-10"})
    assert response.status_code == 400
    assert "公司" in response.get_json()["error"]


def test_create_rejects_bad_date(auth_client):
    response = auth_client.post("/api/applications", json=make_record(apply_date="2026/11/10"))
    assert response.status_code == 400
    assert "YYYY-MM-DD" in response.get_json()["error"]


def test_create_rejects_unknown_status(auth_client):
    response = auth_client.post("/api/applications", json=make_record(status="未知状态"))
    assert response.status_code == 400


def test_list_returns_pagination_envelope(auth_client):
    create(auth_client)
    data = auth_client.get("/api/applications").get_json()
    assert set(data) == {"items", "total", "page", "page_size", "pages"}
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_partial_update_only_touches_given_field(auth_client):
    record = create(auth_client)
    response = auth_client.put(f"/api/applications/{record['id']}", json={"status": "一面"})

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["status"] == "一面"
    # 未提交的字段保持原值
    assert updated["company"] == record["company"]
    assert updated["note"] == record["note"]
    assert updated["updated_at"] >= record["updated_at"]


def test_update_missing_record_returns_404(auth_client):
    response = auth_client.put("/api/applications/9999", json={"status": "一面"})
    assert response.status_code == 404


def test_update_with_empty_payload_returns_400(auth_client):
    record = create(auth_client)
    response = auth_client.put(f"/api/applications/{record['id']}", json={})
    assert response.status_code == 400


def test_delete_record(auth_client):
    record = create(auth_client)
    assert auth_client.delete(f"/api/applications/{record['id']}").status_code == 204
    assert auth_client.delete(f"/api/applications/{record['id']}").status_code == 404


def test_pagination_splits_pages(auth_client):
    for index in range(12):
        create(auth_client, company=f"公司{index:02d}", apply_date=f"2026-11-{index + 1:02d}")

    first = auth_client.get("/api/applications?page=1&page_size=5").get_json()
    assert first["total"] == 12
    assert first["pages"] == 3
    assert len(first["items"]) == 5

    last = auth_client.get("/api/applications?page=3&page_size=5").get_json()
    assert len(last["items"]) == 2

    # 超出范围的页码回退到最后一页，而不是返回空白
    overflow = auth_client.get("/api/applications?page=99&page_size=5").get_json()
    assert overflow["page"] == 3
    assert len(overflow["items"]) == 2


def test_page_size_is_capped(auth_client):
    create(auth_client)
    data = auth_client.get("/api/applications?page_size=9999").get_json()
    assert data["page_size"] == 100


def test_filter_by_keyword_and_status(auth_client):
    create(auth_client, company="新意科技", status="笔试")
    create(auth_client, company="东衡光通讯", status="已投递")

    by_keyword = auth_client.get("/api/applications?keyword=新意").get_json()
    assert by_keyword["total"] == 1
    assert by_keyword["items"][0]["company"] == "新意科技"

    by_status = auth_client.get("/api/applications?status=已投递").get_json()
    assert by_status["total"] == 1
    assert by_status["items"][0]["company"] == "东衡光通讯"


def test_stats_aggregation(auth_client):
    create(auth_client, status="笔试", channel="官网")
    create(auth_client, status="Offer", channel="内推")
    create(auth_client, status="已挂", channel="官网")

    stats = auth_client.get("/api/stats").get_json()
    assert stats["total"] == 3
    assert stats["interview"] == 2          # 笔试 + Offer
    assert stats["offers"] == 1
    assert stats["interview_rate"] == 66.7
    assert stats["by_status"]["已挂"] == 1
    assert {item["name"]: item["count"] for item in stats["by_channel"]} == {"官网": 2, "内推": 1}


def test_stats_on_empty_database(auth_client):
    stats = auth_client.get("/api/stats").get_json()
    assert stats["total"] == 0
    assert stats["interview_rate"] == 0.0
    assert stats["trend"] == []


def test_timestamp_uses_configured_timezone(auth_client):
    record = create(auth_client)
    expected_day = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    assert record["created_at"].startswith(expected_day)
