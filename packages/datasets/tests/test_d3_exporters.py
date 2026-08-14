import uuid
import json
import pytest
from packages.datasets.models import TrainingExample
from packages.datasets.exporters.jsonl_exporter import JSONLDatasetExporter

def dummy_example(prompt: str, answer: str, metadata: dict = None) -> TrainingExample:
    return TrainingExample(
        dataset_version_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        task_name="dummy",
        prompt=prompt,
        canonical_answer=answer,
        metadata=metadata or {}
    )

def test_empty_export():
    exporter = JSONLDatasetExporter()
    result = exporter.export([])
    assert result.content == b""
    assert result.mime_type == "application/jsonlines"

def test_single_export():
    exporter = JSONLDatasetExporter()
    ex = dummy_example("hello", "world")
    result = exporter.export([ex])
    assert result.content.decode("utf-8").count("\n") == 1
    
    parsed = json.loads(result.content.decode("utf-8").strip())
    assert parsed["prompt"] == "hello"
    assert parsed["canonical_answer"] == "world"

def test_multiple_deterministic_ordering():
    exporter = JSONLDatasetExporter()
    examples = [
        dummy_example("p1", "a1"),
        dummy_example("p2", "a2"),
        dummy_example("p3", "a3")
    ]
    result = exporter.export(examples)
    lines = result.content.decode("utf-8").strip().split("\n")
    assert len(lines) == 3
    
    assert json.loads(lines[0])["prompt"] == "p1"
    assert json.loads(lines[1])["prompt"] == "p2"
    assert json.loads(lines[2])["prompt"] == "p3"

def test_deterministic_byte_serialization():
    exporter = JSONLDatasetExporter()
    ex1 = dummy_example("p", "a", metadata={"b": 2, "a": 1})
    
    res1 = exporter.export([ex1])
    res2 = exporter.export([ex1])
    
    assert res1.content == res2.content
    line = res1.content.decode("utf-8").strip()
    
    # Check that sorting actually worked directly without whitespace
    assert '"metadata":{"a":1,"b":2}' in line

def test_str_null_and_mixed_outputs():
    exporter = JSONLDatasetExporter()
    ex = dummy_example("prompt", "null")  # In TrainingExample, canonical_answer is always str safely encoded inside the extraction component!
    
    # Wait, the D2 Extraction component ensures canonical_answer is a valid JSON string.
    # So if expected output is dict, canonical_answer='{"a":1}'.
    # We must treat `canonical_answer` blindly as string in D3!
    result = exporter.export([ex])
    parsed = json.loads(result.content.decode("utf-8").strip())
    assert parsed["canonical_answer"] == "null"

def test_unicode_content():
    exporter = JSONLDatasetExporter()
    ex = dummy_example("hello 👋", "world 🌍", metadata={"unicode \u1234": "val"})
    result = exporter.export([ex])
    line = result.content.decode("utf-8").strip()
    assert "👋" in line
    assert "🌍" in line
