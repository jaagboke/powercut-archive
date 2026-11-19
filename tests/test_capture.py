import json
from datetime import UTC, datetime

import httpx

from powercuts.capture import capture


def make_client(responses):
    # each request gets the next response in the list
    queue = list(responses)

    def handler(request):
        return queue.pop(0)

    return httpx.Client(transport=httpx.MockTransport(handler))


def at(hour, minute):
    return datetime(2026, 11, 16, hour, minute, tzinfo=UTC)


def read_log(data_dir):
    lines = (data_dir / "poll_log.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def test_first_poll_saves_file(tmp_path):
    client = make_client([httpx.Response(200, content=b"id,status\n1,active\n")])

    record = capture("nged", client, tmp_path, now=at(9, 0))

    assert record["ok"] and record["changed"]
    saved = tmp_path / "raw" / "nged" / "2026-11-16" / "090000Z.csv"
    assert saved.read_bytes() == b"id,status\n1,active\n"


def test_identical_poll_is_logged_but_not_saved(tmp_path):
    body = b"id,status\n1,active\n"
    client = make_client([httpx.Response(200, content=body), httpx.Response(200, content=body)])

    capture("nged", client, tmp_path, now=at(9, 0))
    record = capture("nged", client, tmp_path, now=at(9, 5))

    assert record["ok"] and not record["changed"]
    assert not (tmp_path / "raw" / "nged" / "2026-11-16" / "090500Z.csv").exists()
    assert len(read_log(tmp_path)) == 2


def test_changed_poll_saves_new_file(tmp_path):
    client = make_client([
        httpx.Response(200, content=b"id,status\n1,active\n"),
        httpx.Response(200, content=b"id,status\n1,restored\n"),
    ])

    capture("nged", client, tmp_path, now=at(9, 0))
    record = capture("nged", client, tmp_path, now=at(9, 5))

    assert record["changed"]
    assert (tmp_path / "raw" / "nged" / "2026-11-16" / "090500Z.csv").exists()


def test_server_error_is_logged_and_nothing_saved(tmp_path):
    client = make_client([httpx.Response(500)])

    record = capture("nged", client, tmp_path, now=at(9, 0))

    assert not record["ok"]
    assert "500" in record["error"]
    assert not (tmp_path / "raw").exists()
    assert read_log(tmp_path)[0]["ok"] is False


def test_failed_poll_does_not_reset_last_hash(tmp_path):
    body = b"id,status\n1,active\n"
    client = make_client([
        httpx.Response(200, content=body),
        httpx.Response(503),
        httpx.Response(200, content=body),
    ])

    capture("nged", client, tmp_path, now=at(9, 0))
    capture("nged", client, tmp_path, now=at(9, 5))
    record = capture("nged", client, tmp_path, now=at(9, 10))

    assert not record["changed"]