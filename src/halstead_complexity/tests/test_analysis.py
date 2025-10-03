from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from halstead_complexity import analysis, config


def _config_data(*, paired_delimiters: bool) -> Dict[str, Any]:
    data = config.default_config()
    data["languages"]["python"]["paired_delimiters_single_operator"] = paired_delimiters
    return data


def _write_config(path: Path, *, paired_delimiters: bool) -> Path:
    config_data = _config_data(paired_delimiters=paired_delimiters)
    config.write_config(path, config_data)
    return path


def test_is_odd_raw_metrics(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "config.toml", paired_delimiters=False)
    app_config = config.load_app_config(config_path)

    example_path = Path(__file__).resolve().parent.parent / "examples" / "is_odd.py"

    analyzer = analysis.Analyzer(app_config)
    summary = analyzer.analyze(example_path)

    assert len(summary.files) == 1
    raw = summary.files[0].raw
    assert raw.loc == 12
    assert raw.lloc == 9
    assert raw.sloc == 9
    assert raw.comments == 1
    assert raw.multi == 0
    assert raw.blank == 2
    assert raw.single_comments == 1


def test_is_odd_paired_delimiters_single_operator(tmp_path: Path) -> None:
    example_path = Path(__file__).resolve().parent.parent / "examples" / "is_odd.py"

    default_config_path = _write_config(
        tmp_path / "config_default.toml", paired_delimiters=False
    )
    paired_config_path = _write_config(
        tmp_path / "config_paired.toml", paired_delimiters=True
    )

    default_summary = analysis.Analyzer(
        config.load_app_config(default_config_path)
    ).analyze(example_path)
    paired_summary = analysis.Analyzer(
        config.load_app_config(paired_config_path)
    ).analyze(example_path)

    source_text = example_path.read_text(encoding="utf-8")
    expected_reduction = sum(source_text.count(char) for char in (")", "]", "}"))

    assert (
        paired_summary.halstead.total_operators
        == default_summary.halstead.total_operators - expected_reduction
    )
    assert (
        paired_summary.halstead.total_operators
        < default_summary.halstead.total_operators
    )
