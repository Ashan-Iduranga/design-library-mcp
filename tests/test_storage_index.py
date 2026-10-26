import json

from conftest import make_entry
from designlib import config
from designlib.core import storage
from designlib.core.index import delete_and_unindex, rebuild_index, save_and_index
from designlib.core.search import count_entries, get_entry


def test_save_writes_readable_json():
    entry = make_entry()
    path = storage.save_entry(entry)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["title"] == "Sample card"
    assert storage.load_entry(entry.id) == entry


def test_rebuild_reads_all_json_files(sample_entries):
    config.index_path().unlink()  # the index is disposable
    assert rebuild_index() == 3
    assert count_entries() == 3


def test_invalid_json_file_is_skipped(sample_entries, capsys):
    (config.entries_dir() / "broken.json").write_text('{"title": ""}', encoding="utf-8")
    assert rebuild_index() == 3
    assert "skipping invalid entry broken.json" in capsys.readouterr().err


def test_update_replaces_index_row(sample_entries):
    entry = sample_entries[0]
    entry.title = "Renamed pricing"
    save_and_index(entry)
    assert get_entry(entry.id).title == "Renamed pricing"
    assert count_entries() == 3


def test_delete_removes_file_and_row(sample_entries):
    entry_id = sample_entries[1].id
    assert delete_and_unindex(entry_id)
    assert storage.load_entry(entry_id) is None
    assert get_entry(entry_id) is None
