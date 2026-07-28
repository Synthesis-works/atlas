import json

from pydantic import BaseModel

from services.report.exporters import ExportResult, get_exporter


class DummyItem(BaseModel):
    id: int
    name: str
    metadata: dict


def test_json_exporter():
    exporter = get_exporter("json")
    assert exporter is not None

    data = [
        DummyItem(id=1, name="test1", metadata={"key": "val"}),
        {"id": 2, "name": "test2", "metadata": {"key": "val2"}},
    ]

    result: ExportResult = exporter.export(data)
    assert result.mime_type == "application/json"
    assert result.filename_extension == "json"

    parsed = json.loads(result.content.decode("utf-8"))
    assert len(parsed) == 2
    assert parsed[0]["id"] == 1
    assert parsed[0]["metadata"]["key"] == "val"
    assert parsed[1]["id"] == 2


def test_csv_exporter():
    exporter = get_exporter("csv")
    assert exporter is not None

    data = [
        DummyItem(id=1, name="test1", metadata={"key": "val"}),
        {"id": 2, "name": "test2", "metadata": {"key": "val2"}},
    ]

    result: ExportResult = exporter.export(data)
    assert result.mime_type == "text/csv"
    assert result.filename_extension == "csv"

    content_str = result.content.decode("utf-8")
    assert "id,name,metadata" in content_str
    assert "1,test1," in content_str
    assert "2,test2," in content_str
    assert "{'key': 'val'}" in content_str
