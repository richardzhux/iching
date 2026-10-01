"""Lossless, bounded decoding for private chart archive snapshots."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any
import zlib


CHART_SNAPSHOT_ENCODING = "iching.chart-snapshot.gzip.v1"
CHART_SNAPSHOT_STORAGE_BYTES = 2_097_152
CHART_SNAPSHOT_DECODED_BYTES = 32 * 1024 * 1024


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Compressed chart snapshot contains duplicate JSON keys.")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"Compressed chart snapshot contains invalid JSON number {value}.")


def decode_chart_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the original object while leaving its stored envelope unchanged.

    Legacy plain objects retain their existing representation. Compressed
    objects accept exactly one complete gzip member and at most 32 MiB of
    decoded UTF-8 JSON; decoding never expands an unchecked gzip stream.
    """
    if "_encoding" not in snapshot:
        return snapshot
    if snapshot.get("_encoding") != CHART_SNAPSHOT_ENCODING:
        raise ValueError("Unsupported chart snapshot encoding.")
    if set(snapshot) != {"_encoding", "data"} or not isinstance(snapshot.get("data"), str):
        raise ValueError("Invalid compressed chart snapshot envelope.")
    # JSONB's text representation includes separator spaces. Counting those
    # here keeps the same existing database cap even at its byte boundary.
    if len(json.dumps(snapshot, ensure_ascii=False).encode()) > CHART_SNAPSHOT_STORAGE_BYTES:
        raise ValueError("命盘结果快照不能超过 2 MB。")
    try:
        compressed = base64.b64decode(snapshot["data"], validate=True)
        if base64.b64encode(compressed).decode("ascii") != snapshot["data"]:
            raise ValueError("Invalid compressed chart snapshot base64.")
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decoded = decoder.decompress(compressed, CHART_SNAPSHOT_DECODED_BYTES + 1)
    except (binascii.Error, UnicodeError, zlib.error) as exc:
        raise ValueError("Invalid compressed chart snapshot base64 or gzip data.") from exc
    if len(decoded) > CHART_SNAPSHOT_DECODED_BYTES or decoder.unconsumed_tail:
        raise ValueError("Decoded chart snapshot exceeds 32 MiB.")
    if not decoder.eof or decoder.unused_data:
        raise ValueError("Compressed chart snapshot must contain one complete gzip member.")
    try:
        result = json.loads(
            decoded.decode("utf-8"),
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Compressed chart snapshot must contain valid UTF-8 JSON.") from exc
    if not isinstance(result, dict):
        raise ValueError("Decoded chart snapshot must be a JSON object.")
    return result
