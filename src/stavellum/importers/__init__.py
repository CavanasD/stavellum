"""Read-only FLP and MIDI inputs with actionable import failures."""

from pathlib import Path

from stavellum.models import Diagnostic, ProjectIR


class ImportFailure(ValueError):
    """The input cannot be represented safely; diagnostics accompany the failure."""

    def __init__(self, message: str, diagnostics: list[Diagnostic] | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or [Diagnostic("error", "import_failed", message)]


def import_project(path: str | Path, arrangement_index: int = 0) -> ProjectIR:
    source = Path(path).resolve()
    if not source.is_file():
        raise ImportFailure(f"输入文件不存在：{source}")
    if source.suffix.casefold() == ".flp":
        from .flp import import_flp

        return import_flp(source, arrangement_index)
    if source.suffix.casefold() in (".mid", ".midi"):
        from .midi import import_midi

        if arrangement_index:
            raise ImportFailure("MIDI 文件仅有一个编曲，请选择编曲 0。")
        return import_midi(source)
    raise ImportFailure("请选择 FL Studio 工程（.flp）或 MIDI（.mid / .midi）。")


__all__ = ["ImportFailure", "import_project"]
