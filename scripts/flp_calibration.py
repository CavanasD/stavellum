"""Create an isolated, reproducible native FL curve calibration project.

Uses an Image-Line template and a publicly distributed empty FL save, never a
user's musical project. Open the output in FL Studio and render it to WAV.
"""

import argparse
import array
import json
import math
import struct
import wave
from pathlib import Path

from stavellum.importers.flp import _read_events


def encode_event(eid, value):
    if eid < 192:
        return bytes([eid]) + value
    length = len(value)
    prefix = bytearray()
    while length >= 128:
        prefix.append((length & 127) | 128)
        length >>= 7
    prefix.append(length)
    return bytes([eid]) + prefix + value


def create_calibration(output: Path, public_base: Path, template: Path):
    output.mkdir(parents=True, exist_ok=True)
    wav_path = (output / "constant.wav").resolve()
    with wave.open(str(wav_path), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(48000)
        frames = bytearray()
        for sample in range(48000 * 12):
            value = round(math.sin(2 * math.pi * 1000 * sample / 48000) * 6000)
            frames.extend(struct.pack("<hh", value, value))
        stream.writeframes(frames)
    events, _, _, _ = _read_events(public_base.read_bytes())
    source_events, _, _, _ = _read_events(template.read_bytes())
    auto_block = []
    selected = False
    for event in source_events:
        if event.event_id == 64:
            iid = int.from_bytes(event.value, "little")
            if selected:
                break
            selected = iid == 5
        if selected:
            auto_block.append((event.event_id, event.value))
    original_points = next(value for eid, value in auto_block if eid == 234)
    point_count = struct.unpack_from("<I", original_points, 17)[0]
    tail = original_points[21 + point_count * 24:]
    # FL native rendering confirms incoming endpoint tension. Mode 0 is Single,
    # mode 2 is Hold; mode 6 below also provides an unsupported Wave comparison.
    # Segment lengths are four beats (two seconds at 120 BPM).
    points = [(0, .25, 0, 0), (4, .75, .2438096553, 0x01000000),
              (4, .25, -.6171427965, 0xFF000000), (4, .75, 0, 0x02000000),
              (4, .25, 0, 0x02000006), (4, .75, .5, 0x01000000)]
    curve = original_points[:17] + struct.pack("<I", len(points))
    curve += b"".join(struct.pack("<ddfI", *point) for point in points) + tail
    prepared_auto = []
    for eid, value in auto_block:
        if eid == 64:
            value = struct.pack("<H", 2)
        elif eid in (192, 203):
            value = "Curve Calibration\0".encode("utf-16-le")
        elif eid == 234:
            value = curve
        prepared_auto.append((eid, value))
    channel = None
    inserted_auto = inserted_binding = False
    prepared = []
    for event in events:
        eid, value = event.event_id, event.value
        if eid == 64:
            channel = int.from_bytes(value, "little")
            if not inserted_binding:
                prepared.append((227, struct.pack("<HHIII", 0, 2, 0, 65536, 8) + struct.pack("<I", 469)))
                inserted_binding = True
        if eid == 99 and not inserted_auto:
            prepared.extend(prepared_auto)
            inserted_auto = True
        if eid == 199:
            value = b"26.1.1.5547\0"
        elif eid == 156:
            value = struct.pack("<I", 120000)
        elif eid == 196 and channel == 1:
            value = (str(wav_path) + "\0").encode("utf-16-le")
        elif eid == 233:
            clip = bytearray(value[:88])
            struct.pack_into("<I", clip, 8, 1920)
            auto = bytearray(clip)
            struct.pack_into("<H", auto, 6, 2)
            struct.pack_into("<H", auto, 12, 498)
            value = bytes(clip + auto)
        prepared.append((eid, value))
    payload = b"".join(encode_event(eid, value) for eid, value in prepared)
    path = output / "curves.flp"
    path.write_bytes(struct.pack("<4sIhHH", b"FLhd", 6, 0, 3, 96)
                     + b"FLdt" + struct.pack("<I", len(payload)) + payload)
    print(path.resolve())


def analyze_curve_render(rendered: Path):
    """Recompute the nine native WAV observations per smooth curve."""
    with wave.open(str(rendered), "rb") as stream:
        if stream.getsampwidth() != 2:
            raise ValueError("Export the calibration WAV as 16-bit integer PCM.")
        rate, channels = stream.getframerate(), stream.getnchannels()
        samples = array.array("h", stream.readframes(stream.getnframes()))

    def rms(time):
        begin = round((time - .01) * rate) * channels
        count = round(.02 * rate) * channels
        window = samples[begin:begin + count]
        return math.sqrt(math.fsum(value * value for value in window) / len(window))

    def gain(value):
        return math.expm1(math.log(11) * value) / 10
    times = [4.25, 4.5, 4.75, 5, 5.25, 5.5, 5.75]
    scale = math.fsum(rms(time) / gain(.25 + (time - 4) * .25) for time in times) / len(times)
    events, version, ppq, _ = _read_events(rendered.with_suffix(".flp").read_bytes())
    curve = next(event.value for event in events if event.event_id == 234)
    cases = []
    for index, start, first, last in [(1, 0, .25, .75), (2, 2, .75, .25), (5, 8, .25, .75)]:
        _, _, tension, metadata = struct.unpack_from("<ddfI", curve, 21 + index * 24)
        exponent = -math.log(1_000_000) * tension
        observations = []
        for fraction in [.05, .125, .25, .375, .5, .625, .75, .875, .95]:
            measured_rms = rms(start + 2 * fraction)
            value = math.log1p(10 * measured_rms / scale) / math.log(11)
            expected = first + (last - first) * math.expm1(exponent * fraction) / math.expm1(exponent)
            observations.append({"fraction": fraction, "rms": measured_rms,
                                 "observed_value": value, "formula_value": expected,
                                 "absolute_error": abs(value - expected)})
        cases.append({"tension": tension, "metadata": metadata, "observations": observations,
                      "max_absolute_error": max(point["absolute_error"] for point in observations)})
    result = {"fl_version": version, "ppq": ppq, "static_rms": scale, "cases": cases}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(case["max_absolute_error"] >= .0002 for case in cases):
        raise ValueError("Native curve observation exceeds the calibration tolerance.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", type=Path, help="Recheck a native 16-bit curves.wav render.")
    parser.add_argument("--output", type=Path, default=Path(".cache/importers/calibration"))
    parser.add_argument("--base", type=Path, default=Path(".cache/importers/public/empty-fl2026-sampleplacement.flp"))
    parser.add_argument("--template", type=Path, default=Path("C:/Program Files/Image-Line/FL Studio 2026/Data/Templates/Utility/SFX transitions/SFX transitions.flp"))
    arguments = parser.parse_args()
    if arguments.analyze is not None:
        analyze_curve_render(arguments.analyze)
    else:
        create_calibration(arguments.output, arguments.base, arguments.template)
