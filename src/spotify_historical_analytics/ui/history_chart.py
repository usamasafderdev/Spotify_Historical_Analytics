from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pyqtgraph as pg
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolTip


def observation_timestamp(value: str) -> float:
    return datetime.combine(date.fromisoformat(value), time(), timezone.utc).timestamp()


def history_points(rows: list[dict], cadence: int) -> tuple[list[float], list[float]]:
    timestamps = []
    streams = []
    previous = None
    for row in sorted(rows, key=lambda observation: observation["chart_date"]):
        current = date.fromisoformat(row["chart_date"])
        if previous is not None and (current - previous).days > cadence:
            timestamps.append(observation_timestamp((previous + timedelta(days=cadence)).isoformat()))
            streams.append(float("nan"))
        timestamps.append(observation_timestamp(row["chart_date"]))
        streams.append(float(row["streams"]))
        previous = current
    return timestamps, streams


def render_history(panel, rows: list[dict], chart_type: str) -> None:
    plot = panel.plot
    plot.clear()
    panel.set_empty(not rows)
    if not rows:
        return
    ordered = sorted(rows, key=lambda observation: observation["chart_date"])
    timestamps, streams = history_points(ordered, 7 if chart_type in {"weekly", "weekly_derived"} else 1)
    plot.plot(timestamps, streams, pen=pg.mkPen("#A78BFA", width=2),
              symbol="o", symbolSize=7, symbolBrush="#6D28D9", connect="finite")
    plot.setLabel("left", "Chart streams")
    plot.setLabel("bottom", "Reporting date (UTC)")
    plot.setLimits(yMin=0)
    plot.enableAutoRange(axis="x")
    plot.setYRange(0, max(1, max(float(row["streams"]) for row in ordered)) * 1.05, padding=0)
    observed_dates = [row["chart_date"] for row in ordered]
    tick_step = max(1, (len(ordered) + 5) // 6)
    ticks = [(observation_timestamp(value), value) for value in observed_dates[::tick_step]]
    plot.getAxis("bottom").setTicks([ticks])
    plot.getAxis("bottom").setStyle(autoExpandTextSpace=True, hideOverlappingLabels=True)

    def show_hover(event):
        position = event[0]
        if not plot.sceneBoundingRect().contains(position):
            return
        timestamp = plot.getViewBox().mapSceneToView(position).x()
        nearest = min(ordered, key=lambda row: abs(observation_timestamp(row["chart_date"]) - timestamp))
        period = ""
        if nearest.get("weekly_start"):
            period = f"\nPeriod: {nearest['weekly_start']} to {nearest['weekly_end']}"
        if chart_type == "weekly_derived":
            period += f"\nDaily-derived; observed days: {nearest.get('observed_days', 'unavailable')}/7; missing days excluded"
        QToolTip.showText(QCursor.pos(), f"{nearest['chart_date']}{period}\n{int(nearest['streams']):,} chart streams", panel)

    if hasattr(panel, "history_hover"):
        panel.history_hover.disconnect()
    panel.history_hover = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=30, slot=show_hover)
