"""Offline loader contract and transaction tests."""
import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from aerologix import load as loader


def _write_feed(folder: Path, filename: str, headers: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with (folder / filename).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_all_feed_mappings_match_checked_in_csv_headers():
    folder = ROOT / 'data' / 'raw'
    counts = {feed.filename: len(loader.read_feed(folder, feed)) for feed in loader.FEEDS}
    assert counts == {'airports.csv': 8, 'aircraft.csv': 6, 'routes.csv': 10, 'flights.csv': 120, 'bookings.csv': 1200}


def test_headers_are_explicit_and_null_is_preserved():
    feed = next(x for x in loader.FEEDS if x.filename == 'flights.csv')
    row = loader.read_feed(ROOT / 'data' / 'raw', feed)[36]
    assert row[7] is None
    assert feed.columns[7][:2] == ('actual_departure', 'ActualDeparture')


def test_rejects_missing_headers_and_duplicate_keys(tmp_path):
    feed = loader.FEEDS[0]
    _write_feed(tmp_path, feed.filename, ('airport_code',), [])
    with pytest.raises(loader.FeedValidationError, match='header mismatch'):
        loader.read_feed(tmp_path, feed)
    headers = feed.headers
    row = dict.fromkeys(headers, 'x')
    _write_feed(tmp_path, feed.filename, headers, [row, row])
    with pytest.raises(loader.FeedValidationError, match='duplicate business key'):
        loader.read_feed(tmp_path, feed)


class FakeCursor:
    def __init__(self, fail=False):
        self.fast_executemany = False
        self.statements = []
        self.fail = fail

    def execute(self, statement, *parameters):
        self.statements.append(statement if not parameters else (statement, parameters))
        if self.fail and statement.startswith('EXEC '):
            raise RuntimeError('simulated apply failure')
        return self

    def fetchone(self):
        return (0,)

    def executemany(self, statement, rows):
        self.statements.append((statement, list(rows)))


class FakeConnection:
    def __init__(self, fail=False):
        self.cursor_value = FakeCursor(fail)
        self.committed = self.rolled_back = self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_loader_uses_explicit_mapping_and_commits(monkeypatch):
    monkeypatch.setenv('SQLSERVER_PASSWORD', 'test-only')
    connection = FakeConnection()
    result = loader.load(ROOT / 'data' / 'raw', batch_size=17, connection_factory=lambda _: connection)
    assert result['bookings.csv'] == 1200
    assert connection.committed and connection.closed and not connection.rolled_back
    inserts = [x[0] for x in connection.cursor_value.statements if isinstance(x, tuple)]
    assert any('[TimeZoneName]' in sql for sql in inserts)
    assert any('[BaseFare]' in sql for sql in inserts)
    assert any(isinstance(sql, str) and sql.startswith('EXEC etl.usp_ApplyOperationalLoad')
               for sql in connection.cursor_value.statements)


def test_loader_rolls_back_and_closes_after_failure(monkeypatch):
    monkeypatch.setenv('SQLSERVER_PASSWORD', 'test-only')
    connection = FakeConnection(fail=True)
    with pytest.raises(RuntimeError, match='simulated'):
        loader.load(ROOT / 'data' / 'raw', connection_factory=lambda _: connection)
    # The RUNNING audit row is committed before the data transaction so failures remain visible.
    assert connection.rolled_back and connection.closed and connection.committed


def test_generator_options_and_invalid_capacity(tmp_path):
    from aerologix.generate import generate
    generate(tmp_path, 4, 3, seed=55, start_date='2026-02-01', days=2)
    with (tmp_path / 'flights.csv').open(newline='', encoding='utf-8') as handle:
        flights = list(csv.DictReader(handle))
    assert flights[0]['flight_date'] == '2026-02-01'
    with pytest.raises(ValueError, match='capacity'):
        generate(tmp_path, 1, 181)


def test_resilient_reader_preserves_invalid_records(tmp_path):
    feed = next(x for x in loader.FEEDS if x.filename == 'airports.csv')
    _write_feed(tmp_path, feed.filename, feed.headers, [
        dict(zip(feed.headers, ('JFK', 'John F Kennedy', 'New York', 'US', 'America/New_York'))),
        dict(zip(feed.headers, ('BAD', '', 'City', 'US', 'Etc/UTC'))),
    ])
    accepted, rejected = loader.read_feed_resilient(tmp_path, feed)
    assert len(accepted) == 1
    assert rejected[0]['row_number'] == 3
    assert rejected[0]['record']['airport_code'] == 'BAD'
    assert 'required value' in rejected[0]['reason']


def test_loader_quarantines_invalid_rows_and_loads_valid_rows(tmp_path, monkeypatch):
    import json
    import shutil
    source = tmp_path / 'source'
    source.mkdir()
    for feed in loader.FEEDS:
        shutil.copy(ROOT / 'data' / 'raw' / feed.filename, source / feed.filename)
    airports = source / 'airports.csv'
    with airports.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    rows[0]['airport_name'] = ''
    _write_feed(source, 'airports.csv', loader.FEEDS[0].headers, rows)
    monkeypatch.setenv('SQLSERVER_PASSWORD', 'test-only')
    connection = FakeConnection()
    result = loader.load(source, connection_factory=lambda _: connection,
                        quarantine_dir=tmp_path / 'quarantine')
    assert result['airports.csv'] == 7
    files = list((tmp_path / 'quarantine').glob('*.jsonl'))
    assert len(files) == 1
    rejected = json.loads(files[0].read_text(encoding='utf-8').splitlines()[0])
    assert rejected['record']['airport_code'] == 'JFK'
    assert 'required value' in rejected['reason']
    assert connection.committed and not connection.rolled_back
