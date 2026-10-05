from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

path = Path(__file__).resolve().parents[1] / "scripts/verify_rhi_batch.py"
spec = importlib.util.spec_from_file_location("rhi_batch_benchmark", path)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def results(batch2=8, batch4=7.9, baseline=10):
    return [{"case": case, "mode": mode, "repeat": repeat, "pipeline_seconds": seconds}
            for case in benchmark.CASES
            for mode, seconds in zip(benchmark.MODES, (baseline, baseline, batch2, batch4), strict=True)
            for repeat in (1, 2, 3)]


def test_gate_prefers_two_when_both_pass_and_four_has_under_three_percent_gain():
    _, gate = benchmark.medians_and_gate(results(), True)
    assert gate["full_song_gate_passed"]
    assert gate["selected_mode"] == "batch2"
    assert gate["candidates"]["batch2"]["aggregate_export_reduction"] == pytest.approx(.2)
    assert gate["batch2_batch4_relative_difference"] < .03


def test_gate_requires_meaningful_gain_and_reviewed_quality():
    assert not benchmark.medians_and_gate(results(batch2=9.6, batch4=9.6), True)[1]["full_song_gate_passed"]
    assert benchmark.medians_and_gate(results(batch2=9.5, batch4=9.5), True)[1]["full_song_gate_passed"]
    assert not benchmark.medians_and_gate(results(), False)[1]["full_song_gate_passed"]
    assert benchmark.medians_and_gate(results(batch2=8.5, batch4=8), True)[1]["selected_mode"] == "batch4"


def test_regressing_scene_excludes_candidate_even_with_large_aggregate_gain():
    rows = results(batch2=5, batch4=6)
    for row in rows:
        if row["case"] == "dense" and row["mode"] == "batch2":
            row["pipeline_seconds"] = 10.6
    _, gate = benchmark.medians_and_gate(rows, True)
    assert not gate["candidates"]["batch2"]["passed"]
    assert gate["candidates"]["batch2"]["regressing_cases_over_5_percent"] == ["dense"]
    assert gate["selected_mode"] == "batch4"


def test_partial_rounds_never_unlock_full_export():
    rows = [row for row in results() if not (row["case"] == "4k" and row["repeat"] == 3)]
    _, gate = benchmark.medians_and_gate(rows, True)
    assert not gate["complete_three_rounds"]
    assert not gate["full_song_gate_passed"]
    assert gate["selected_mode"] is None


def test_runs_are_rotated_and_quality_has_consecutive_frames_and_short_tail():
    assert benchmark.alternating_modes(benchmark.MODES, 1) == benchmark.MODES
    assert benchmark.alternating_modes(benchmark.MODES, 2) == ("batch1", "batch2", "batch4", "baseline")
    assert benchmark.alternating_modes(("baseline", "batch2"), 2) == ("batch2", "baseline")
    samples = benchmark.quality_times(82)
    assert len(samples) == 13 and samples[:5] == [82 + i / 60 for i in range(5)]
    assert samples[-1] == pytest.approx(90 - 1 / 60)


def test_quality_gate_requires_every_case_mode_exact_and_decoded():
    quality = [{"case": case, "mode": mode, "exact_raw_bytes_equal": True,
                "mp4": {"decoded_successfully": True}, "gpu_identity": "same gpu"}
               for case in benchmark.CASES for mode in benchmark.MODES]
    report = {"quality": quality, "local": results(), "visual_review_recorded": True}
    for row in report["local"]:
        row["gpu_identity"] = "same gpu"
    benchmark.summarize(report)
    assert report["gate"]["full_song_gate_passed"]
    quality[-1]["exact_raw_bytes_equal"] = False
    benchmark.summarize(report)
    assert not report["quality_gate"]["passed"]
    quality[-1]["gpu_identity"] = "different gpu"
    with pytest.raises(RuntimeError, match="different hardware GPUs"):
        benchmark.summarize(report)


def test_worker_subprocess_pins_package_dll_and_batch_without_parent_environment_leak(tmp_path, monkeypatch):
    result = tmp_path / "result.json"
    worker_spec = {"result": str(result), "mode": "batch4", "source": str(tmp_path / "src"),
                   "dll": str(tmp_path / "matching.dll"), "case": "dense", "repeat": 1}
    calls = []

    def run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        benchmark.write_report(result, {"status": "complete"})
        return SimpleNamespace(returncode=0)

    monkeypatch.setenv("PYTHONPATH", "parent-package")
    monkeypatch.setenv("STAVELLUM_RHI_DLL", "parent.dll")
    monkeypatch.setattr(benchmark.subprocess, "run", run)
    actual = benchmark.run_worker("local", worker_spec)
    environment = calls[0][1]["env"]
    assert environment["PYTHONPATH"] == worker_spec["source"]
    assert environment["STAVELLUM_RHI_DLL"] == worker_spec["dll"]
    assert environment["STAVELLUM_RHI_BATCH_SIZE"] == "4"
    assert environment["STAVELLUM_RHI_TIMESTAMPS"] == "0"
    assert actual["repeat"] == 1 and actual["case"] == "dense"
    assert "--worker" in calls[0][0]
    assert json.loads(result.read_text(encoding="utf-8"))["status"] == "complete"


def test_mp4_verification_actually_decodes_audio_video_and_rejects_shape(tmp_path, monkeypatch):
    output = tmp_path / "output.mp4"
    output.write_bytes(b"encoded fixture")
    streams = [{"codec_type": "video", "codec_name": "h264", "nb_read_frames": "60",
                "width": 1920, "height": 1080, "avg_frame_rate": "60/1"},
               {"codec_type": "audio", "codec_name": "aac", "channels": 2}]
    calls = []

    def run(arguments, **kwargs):
        calls.append(arguments)
        return SimpleNamespace(stderr=b"", stdout=json.dumps({"streams": streams}).encode())

    monkeypatch.setattr(benchmark.subprocess, "run", run)
    verified = benchmark.verify_mp4("ffmpeg", "ffprobe", output, 60, 1920, 1080)
    assert verified["decoded_successfully"]
    assert "0:v:0" in calls[0] and "0:a:0" in calls[0] and "null" in calls[0]
    assert "-count_frames" in calls[1]
    streams[1]["channels"] = 1
    with pytest.raises(RuntimeError, match="contract failed"):
        benchmark.verify_mp4("ffmpeg", "ffprobe", output, 60, 1920, 1080)


def test_rerun_replaces_same_round_without_displacing_other_measurements():
    report = {"local": []}
    row = {"project": "song", "case": "dense", "mode": "batch2", "repeat": 1, "pipeline_seconds": 9}
    benchmark.update_result(report, "local", row)
    benchmark.update_result(report, "local", {**row, "repeat": 2})
    benchmark.update_result(report, "local", {**row, "pipeline_seconds": 8})
    assert len(report["local"]) == 2
    assert next(item for item in report["local"] if item["repeat"] == 1)["pipeline_seconds"] == 8


def test_full_summary_uses_export_wall_and_requires_both_projects_and_all_rounds(tmp_path):
    projects = (tmp_path / "first.stproj", tmp_path / "second.stproj")
    rows = [{"project": str(project), "mode": mode, "repeat": repeat, "frames": 100,
             "pipeline_seconds": seconds, "total_wall_seconds": seconds + 30, "compile_seconds": 25}
            for project in projects for mode, seconds in (("baseline", 10), ("batch2", 8))
            for repeat in (1, 2, 3)]
    medians, gate = benchmark.full_summary(rows, "batch2", True, projects=projects)
    assert gate["passed"] and gate["aggregate_export_reduction"] == pytest.approx(.2)
    assert medians[str(projects[0])]["batch2"]["pipeline_seconds"] == 8
    assert medians[str(projects[0])]["batch2"]["total_wall_seconds"] == 38
    assert not benchmark.full_summary(rows[:-1], "batch2", True, projects=projects)[1]["passed"]
    assert not benchmark.full_summary(rows, "batch2", False, projects=projects)[1]["passed"]
    rows[-1]["frames"] = 101
    with pytest.raises(RuntimeError, match="different frame counts"):
        benchmark.full_summary(rows, "batch2", True, projects=projects)


def test_project_fingerprints_resolve_relative_audio_and_record_content(tmp_path):
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"original audio")
    project = tmp_path / "song.stproj"
    project.write_text(json.dumps({"audio_path": "source.wav"}), encoding="utf-8")
    original = benchmark.project_fingerprints(project)
    assert original["audio"] == str(audio)
    assert original["project_sha256"] == benchmark.fingerprint(project)
    audio.write_bytes(b"different audio")
    assert benchmark.project_fingerprints(project)["audio_sha256"] != original["audio_sha256"]
    audio.unlink()
    with pytest.raises(FileNotFoundError, match="audio is missing"):
        benchmark.project_fingerprints(project)


def test_shared_scene_fingerprint_mismatch_blocks_comparison():
    report = {"local": [{"case": "intro", "mode": mode, "repeat": 1,
                         "pipeline_seconds": 10, "gpu_identity": "same gpu", "scene_sha256": digest}
                        for mode, digest in (("baseline", "old-scene"), ("batch2", "other-scene"))]}
    with pytest.raises(RuntimeError, match="Comparison inputs differ"):
        benchmark.summarize(report)
