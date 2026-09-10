"""Warm and differential color palettes for terminal flamegraphs and TUI."""

from __future__ import annotations


class FlameColorPalette:
    """Provides gradient color mappings for memory allocation intensities."""

    # Warm flame scale: dark red -> crimson -> dark orange -> amber -> gold -> bright yellow
    WARM_HEX = [
        "#8B0000",
        "#B22222",
        "#D32F2F",
        "#E65100",
        "#F57C00",
        "#FF9800",
        "#FFA726",
        "#FFB74D",
        "#FFD54F",
        "#FFEE58",
    ]

    # Differential scale: blue (optimized) -> gray (unchanged) -> red (regression)
    DIFF_REDUCTION_HEX = ["#0D47A1", "#1976D2", "#2196F3", "#64B5F6"]
    DIFF_NEUTRAL_HEX = "#757575"
    DIFF_INCREASE_HEX = ["#EF5350", "#E53935", "#C62828", "#B71C1C"]

    @classmethod
    def get_warm_color(cls, percentage: float) -> str:
        """Map percentage (0.0 - 100.0) to a warm flame hex color."""
        clamped = max(0.0, min(100.0, percentage))
        index = int((clamped / 100.0) * (len(cls.WARM_HEX) - 1))
        return cls.WARM_HEX[index]

    @classmethod
    def get_warm_ansi(cls, percentage: float) -> str:
        """Map percentage to ANSI 256 color code."""
        clamped = max(0.0, min(100.0, percentage))
        # ANSI 256 colors: 52 (dark red), 88, 124, 160, 196, 202, 208, 214, 220, 226 (yellow)
        ansi_scale = [52, 88, 124, 160, 196, 202, 208, 214, 220, 226]
        index = int((clamped / 100.0) * (len(ansi_scale) - 1))
        return f"\033[38;5;{ansi_scale[index]}m"

    @classmethod
    def get_diff_color(cls, delta_bytes: int, max_delta: int) -> str:
        """Map a differential memory delta to red (growth) or blue (reduction)."""
        if delta_bytes == 0 or max_delta == 0:
            return cls.DIFF_NEUTRAL_HEX

        ratio = min(1.0, abs(delta_bytes) / max_delta)
        if delta_bytes > 0:
            idx = int(ratio * (len(cls.DIFF_INCREASE_HEX) - 1))
            return cls.DIFF_INCREASE_HEX[idx]
        else:
            idx = int(ratio * (len(cls.DIFF_REDUCTION_HEX) - 1))
            return cls.DIFF_REDUCTION_HEX[idx]

    @classmethod
    def get_diff_ansi(cls, delta_bytes: int, max_delta: int) -> str:
        """Return ANSI escape code for differential rendering."""
        if delta_bytes == 0 or max_delta == 0:
            return "\033[38;5;245m"  # Gray

        ratio = min(1.0, abs(delta_bytes) / max_delta)
        if delta_bytes > 0:
            # 160, 196, 197, 203 (Reds)
            reds = [203, 197, 196, 160]
            idx = int(ratio * (len(reds) - 1))
            return f"\033[38;5;{reds[idx]}m"
        else:
            # 39, 33, 27, 21 (Blues)
            blues = [39, 33, 27, 21]
            idx = int(ratio * (len(blues) - 1))
            return f"\033[38;5;{blues[idx]}m"
