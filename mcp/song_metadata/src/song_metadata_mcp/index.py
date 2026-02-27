from __future__ import annotations

import bisect
import json
import math
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .errors import QueryError
from .models import FeatureSeries, SongIndex


class MetadataIndexStore:
    def __init__(self, meta_root: Path, max_raw_points: int, default_max_points: int) -> None:
        self.meta_root = meta_root
        self.max_raw_points = max_raw_points
        self.default_max_points = default_max_points
        self._cache: Dict[str, SongIndex] = {}

    def list_songs(self) -> List[str]:
        if not self.meta_root.exists():
            return []
        songs: List[str] = []
        for child in self.meta_root.iterdir():
            if child.is_dir() and (child / "info.json").exists():
                songs.append(child.name)
        return sorted(songs)

    def list_features(self, song: str) -> Dict[str, Any]:
        index = self._get_song(song)
        feature_names = sorted(index.features.keys())
        return self._ok(
            {
                "song": song,
                "features": feature_names,
                "feature_count": len(feature_names),
                "duration": self._song_duration(index),
            }
        )

    def get_song_overview(self, song: str) -> Dict[str, Any]:
        index = self._get_song(song)
        info = index.info
        beat_tracking = info.get("beat_tracking") if isinstance(info, dict) else {}
        beats_count = len(index.features.get("analyzer.beats", FeatureSeries("", "", Path("."), None, None, None)).times)
        downbeats_count = len(
            index.features.get("analyzer.downbeats", FeatureSeries("", "", Path("."), None, None, None)).times
        )

        return self._ok(
            {
                "song": song,
                "duration": self._song_duration(index),
                "tempo_bpm": beat_tracking.get("tempo_bpm") if isinstance(beat_tracking, dict) else None,
                "key": self._extract_key(info),
                "beats_count": beats_count,
                "downbeats_count": downbeats_count,
                "feature_count": len(index.features),
                "sources": sorted({series.source for series in index.features.values()}),
            }
        )

    def query_feature(
        self,
        song: str,
        feature: str,
        start_time: Optional[float],
        end_time: Optional[float],
        include_raw: bool,
        mode: str,
        max_points: Optional[int],
        time_tolerance_ms: float,
    ) -> Dict[str, Any]:
        index = self._get_song(song)
        series = index.features.get(feature)
        if series is None:
            raise QueryError("feature_not_found", f"Feature '{feature}' not found", {"song": song, "feature": feature})

        result = self._slice_series(
            series=series,
            start_time=start_time,
            end_time=end_time,
            include_raw=include_raw,
            mode=mode,
            max_points=max_points,
            time_tolerance_ms=time_tolerance_ms,
        )
        return self._ok({"song": song, "feature": feature, **result})

    def query_window(
        self,
        song: str,
        start_time: float,
        end_time: float,
        features: List[str],
        include_raw: bool,
        mode: str,
        max_points: Optional[int],
        time_tolerance_ms: float,
    ) -> Dict[str, Any]:
        index = self._get_song(song)
        if not features:
            raise QueryError("data_unavailable", "At least one feature is required", {"song": song})

        results: Dict[str, Any] = {}
        for feature in features:
            series = index.features.get(feature)
            if series is None:
                raise QueryError("feature_not_found", f"Feature '{feature}' not found", {"song": song, "feature": feature})
            results[feature] = self._slice_series(
                series=series,
                start_time=start_time,
                end_time=end_time,
                include_raw=include_raw,
                mode=mode,
                max_points=max_points,
                time_tolerance_ms=time_tolerance_ms,
            )

        return self._ok(
            {
                "song": song,
                "window": {"start_time": start_time, "end_time": end_time},
                "mode": mode,
                "features": results,
            }
        )

    def _ok(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "data": data}

    def to_error(self, error: QueryError) -> Dict[str, Any]:
        return {"ok": False, "error": error.to_dict()}

    def _get_song(self, song: str) -> SongIndex:
        song_dir = self.meta_root / song
        if not song_dir.exists() or not song_dir.is_dir():
            raise QueryError("song_not_found", f"Song '{song}' not found", {"song": song})

        signature = self._signature(song_dir)
        cached = self._cache.get(song)
        if cached and cached.signature == signature:
            return cached

        built = self._build_song_index(song, song_dir, signature)
        self._cache[song] = built
        return built

    def _signature(self, song_dir: Path) -> Dict[str, float]:
        signature: Dict[str, float] = {}
        for path in sorted(song_dir.rglob("*.json")):
            try:
                signature[str(path.relative_to(song_dir))] = path.stat().st_mtime
            except OSError:
                continue
        return signature

    def _build_song_index(self, song: str, song_dir: Path, signature: Dict[str, float]) -> SongIndex:
        info = self._load_json(song_dir / "info.json", default={})
        features: Dict[str, FeatureSeries] = {}

        self._load_analyzer_beats(song_dir, features)
        self._load_essentia(song_dir, features)
        self._load_moises(song_dir, features)

        if not features:
            raise QueryError("data_unavailable", "No queryable features found", {"song": song})

        return SongIndex(song=song, song_dir=song_dir, info=info, features=features, signature=signature)

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return default

    def _load_analyzer_beats(self, song_dir: Path, features: Dict[str, FeatureSeries]) -> None:
        data = self._load_json(song_dir / "beats.json", default={})
        if not isinstance(data, dict):
            return

        for key in ("beats", "downbeats"):
            arr = data.get(key)
            if not isinstance(arr, list):
                continue
            times = self._to_float_list(arr)
            if not times:
                continue
            values = [1.0] * len(times)
            features[f"analyzer.{key}"] = FeatureSeries(
                name=f"analyzer.{key}",
                source="analyzer",
                path=song_dir / "beats.json",
                part=None,
                duration=max(times),
                sample_rate=None,
                times=times,
                values=values,
                metadata={"kind": key},
            )

    def _load_essentia(self, song_dir: Path, features: Dict[str, FeatureSeries]) -> None:
        essentia_dir = song_dir / "essentia"
        if not essentia_dir.exists():
            return

        for path in sorted(essentia_dir.glob("*.json")):
            data = self._load_json(path, default={})
            if not isinstance(data, dict):
                continue

            stem = path.stem
            times = self._to_float_list(data.get("times") or [])
            sample_rate = self._to_float(data.get("sample_rate"))
            duration = self._to_float(data.get("duration"))
            part = data.get("part") if isinstance(data.get("part"), str) else None

            if times:
                for key, values in data.items():
                    if key in {"times", "part", "sample_rate", "duration", "frame_size", "hop_size"}:
                        continue
                    if not isinstance(values, list) or len(values) != len(times):
                        continue

                    numeric = self._series_values(values)
                    if numeric is None:
                        continue

                    name = f"essentia.{stem}.{key}"
                    features[name] = FeatureSeries(
                        name=name,
                        source="essentia",
                        path=path,
                        part=part,
                        duration=duration,
                        sample_rate=sample_rate,
                        times=times,
                        values=numeric,
                        metadata={"field": key},
                    )

            self._load_essentia_nested(path, data, stem, part, duration, sample_rate, features)

    def _load_essentia_nested(
        self,
        path: Path,
        data: Dict[str, Any],
        stem: str,
        part: Optional[str],
        duration: Optional[float],
        sample_rate: Optional[float],
        features: Dict[str, FeatureSeries],
    ) -> None:
        rhythm = data.get("rhythm")
        if isinstance(rhythm, dict):
            for key in ("beats", "downbeats"):
                arr = rhythm.get(key)
                if not isinstance(arr, list):
                    continue
                times = self._to_float_list(arr)
                if not times:
                    continue
                name = f"essentia.{stem}.rhythm.{key}"
                features[name] = FeatureSeries(
                    name=name,
                    source="essentia",
                    path=path,
                    part=part,
                    duration=duration,
                    sample_rate=sample_rate,
                    times=times,
                    values=[1.0] * len(times),
                    metadata={"field": key},
                )

        onsets = data.get("onsets")
        if isinstance(onsets, dict):
            arr = onsets.get("times")
            if isinstance(arr, list):
                times = self._to_float_list(arr)
                if times:
                    name = f"essentia.{stem}.onsets.times"
                    features[name] = FeatureSeries(
                        name=name,
                        source="essentia",
                        path=path,
                        part=part,
                        duration=duration,
                        sample_rate=sample_rate,
                        times=times,
                        values=[1.0] * len(times),
                        metadata={"field": "onsets.times"},
                    )

    def _load_moises(self, song_dir: Path, features: Dict[str, FeatureSeries]) -> None:
        moises_dir = song_dir / "moises"
        if not moises_dir.exists():
            return

        beats_path = moises_dir / "beats.json"
        beats_data = self._load_json(beats_path, default=[])
        if isinstance(beats_data, list) and beats_data:
            times: List[float] = []
            beat_nums: List[float] = []
            for row in beats_data:
                if not isinstance(row, dict):
                    continue
                raw_time = row.get("time")
                if raw_time is None:
                    continue
                time_value = self._to_float(raw_time)
                if time_value is None:
                    continue
                beat_num = self._to_float(row.get("beatNum")) or 0.0
                times.append(time_value)
                beat_nums.append(beat_num)

            if times:
                features["moises.beats.time"] = FeatureSeries(
                    name="moises.beats.time",
                    source="moises",
                    path=beats_path,
                    part=None,
                    duration=max(times),
                    sample_rate=None,
                    times=times,
                    values=[1.0] * len(times),
                    metadata={"field": "time"},
                )
                features["moises.beats.beat_num"] = FeatureSeries(
                    name="moises.beats.beat_num",
                    source="moises",
                    path=beats_path,
                    part=None,
                    duration=max(times),
                    sample_rate=None,
                    times=times,
                    values=beat_nums,
                    metadata={"field": "beatNum"},
                )

    def _slice_series(
        self,
        series: FeatureSeries,
        start_time: Optional[float],
        end_time: Optional[float],
        include_raw: bool,
        mode: str,
        max_points: Optional[int],
        time_tolerance_ms: float,
    ) -> Dict[str, Any]:
        if mode not in {"summary", "exact"}:
            raise QueryError("invalid_time_range", "mode must be 'summary' or 'exact'", {"mode": mode})

        if not series.times or not series.values:
            raise QueryError("data_unavailable", f"Feature '{series.name}' has no data")

        start = series.times[0] if start_time is None else float(start_time)
        end = series.times[-1] if end_time is None else float(end_time)

        if end < start:
            raise QueryError(
                "invalid_time_range",
                "end_time must be greater than or equal to start_time",
                {"start_time": start, "end_time": end},
            )

        tolerance_seconds = max(0.0, float(time_tolerance_ms) / 1000.0)
        query_start = start - tolerance_seconds
        query_end = end + tolerance_seconds

        lo = bisect.bisect_left(series.times, query_start)
        hi = bisect.bisect_right(series.times, query_end)
        sliced_times = series.times[lo:hi]
        sliced_values = series.values[lo:hi]

        summary = self._summary(sliced_times, sliced_values)
        payload: Dict[str, Any] = {
            "summary": summary,
            "window": {"start_time": start, "end_time": end},
            "resolved_window": {
                "start_time": sliced_times[0] if sliced_times else None,
                "end_time": sliced_times[-1] if sliced_times else None,
                "time_tolerance_ms": time_tolerance_ms,
            },
            "mode": mode,
            "source": series.source,
            "part": series.part,
            "sample_rate": series.sample_rate,
            "duration": series.duration,
        }

        if not include_raw:
            return payload

        if mode == "exact":
            if len(sliced_times) > self.max_raw_points:
                raise QueryError(
                    "payload_too_large",
                    "Exact mode exceeded raw point cap",
                    {"points": len(sliced_times), "max_raw_points": self.max_raw_points},
                )
            payload["raw"] = {"times": sliced_times, "values": sliced_values, "points": len(sliced_times)}
            return payload

        target = self.default_max_points if max_points is None else int(max_points)
        if target <= 0:
            raise QueryError("invalid_time_range", "max_points must be greater than 0", {"max_points": target})
        decimated_times, decimated_values = self._decimate(sliced_times, sliced_values, target)

        if len(decimated_times) > self.max_raw_points:
            raise QueryError(
                "payload_too_large",
                "Summary mode raw payload exceeded cap",
                {"points": len(decimated_times), "max_raw_points": self.max_raw_points},
            )

        payload["raw"] = {
            "times": decimated_times,
            "values": decimated_values,
            "points": len(decimated_times),
            "decimated": len(decimated_times) != len(sliced_times),
        }
        return payload

    def _summary(self, times: List[float], values: List[float]) -> Dict[str, Any]:
        if not times or not values:
            return {
                "points": 0,
                "min": None,
                "max": None,
                "mean": None,
                "std": None,
                "first_time": None,
                "last_time": None,
            }

        std = pstdev(values) if len(values) > 1 else 0.0
        return {
            "points": len(values),
            "min": min(values),
            "max": max(values),
            "mean": fmean(values),
            "std": std,
            "first_time": times[0],
            "last_time": times[-1],
        }

    def _decimate(self, times: List[float], values: List[float], target: int) -> Tuple[List[float], List[float]]:
        if len(times) <= target:
            return times, values
        if target < 2:
            return [times[0]], [values[0]]

        step = (len(times) - 1) / float(target - 1)
        idxs = sorted({min(len(times) - 1, int(round(i * step))) for i in range(target)})
        dec_times = [times[idx] for idx in idxs]
        dec_values = [values[idx] for idx in idxs]
        return dec_times, dec_values

    def _song_duration(self, index: SongIndex) -> Optional[float]:
        info = index.info
        beat_tracking = info.get("beat_tracking") if isinstance(info, dict) else None
        if isinstance(beat_tracking, dict):
            beats = beat_tracking.get("beat_count")
            if isinstance(beats, (int, float)) and beats > 0:
                pass

        durations = [feature.duration for feature in index.features.values() if isinstance(feature.duration, (int, float))]
        if durations:
            return float(max(durations))
        return None

    def _extract_key(self, info: Dict[str, Any]) -> Optional[str]:
        if not isinstance(info, dict):
            return None
        if isinstance(info.get("key"), str):
            return info["key"]
        return None

    def _series_values(self, values: List[Any]) -> Optional[List[float]]:
        if not values:
            return []

        first = values[0]
        if isinstance(first, list):
            out: List[float] = []
            for row in values:
                if not isinstance(row, list) or not row:
                    out.append(0.0)
                    continue
                numeric = [self._to_float(x) for x in row]
                cleaned = [x for x in numeric if x is not None]
                out.append(fmean(cleaned) if cleaned else 0.0)
            return out

        numeric = self._to_float_list(values)
        if len(numeric) != len(values):
            return None
        return numeric

    def _to_float(self, value: Any) -> Optional[float]:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            val = float(value)
            if math.isfinite(val):
                return val
            return None
        try:
            val = float(value)
            if math.isfinite(val):
                return val
        except Exception:
            return None
        return None

    def _to_float_list(self, values: Iterable[Any]) -> List[float]:
        out: List[float] = []
        for value in values:
            numeric = self._to_float(value)
            if numeric is None:
                continue
            out.append(numeric)
        return out
