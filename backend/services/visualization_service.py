"""Visualization service for selecting a safe, sensible Plotly chart from query output."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


CHART_COLORS = ["#7CF0C7", "#5BCCE2", "#FFB870", "#8C8CFF", "#FF7F8D", "#A7F06B", "#FFD86A", "#6FA8FF"]


def build_chart(df: pd.DataFrame):
    if df is None:
        return _empty_figure("No data available.")

    if df.empty:
        return _empty_figure("Query returned no rows.")

    safe_df = df.copy()
    numeric_columns = safe_df.select_dtypes(include="number").columns.tolist()
    datetime_columns = []
    categorical_columns = []
    low_cardinality_numeric_columns = []

    for column in safe_df.columns:
        if pd.api.types.is_datetime64_any_dtype(safe_df[column]):
            datetime_columns.append(column)
            continue
        if safe_df[column].dtype == object:
            converted = pd.to_datetime(safe_df[column], errors="coerce")
            if converted.notna().sum() >= max(1, len(safe_df) // 2):
                safe_df[column] = converted
                datetime_columns.append(column)
                continue
        categorical_columns.append(column)
        if column in numeric_columns and safe_df[column].nunique(dropna=True) <= min(12, max(2, len(safe_df))):
            low_cardinality_numeric_columns.append(column)

    try:
        if datetime_columns and numeric_columns:
            return px.line(
                safe_df.sort_values(datetime_columns[0]),
                x=datetime_columns[0],
                y=numeric_columns[0],
                markers=True,
                title=f"{numeric_columns[0]} over {datetime_columns[0]}",
                color_discrete_sequence=CHART_COLORS,
            )

        if len(safe_df.columns) == 1 and len(numeric_columns) == 1:
            return px.histogram(
                safe_df,
                x=numeric_columns[0],
                nbins=min(20, max(5, len(safe_df))),
                title=f"Distribution of {numeric_columns[0]}",
                color_discrete_sequence=CHART_COLORS,
            )

        if len(safe_df.columns) == 2 and len(numeric_columns) == 1:
            value_column = numeric_columns[0]
            category_column = next((col for col in safe_df.columns if col != value_column), None)
            if category_column:
                if safe_df[category_column].nunique(dropna=True) <= 5:
                    return px.pie(
                        safe_df,
                        names=category_column,
                        values=value_column,
                        title=f"{value_column} share by {category_column}",
                        color_discrete_sequence=CHART_COLORS,
                    )
                return px.bar(
                    safe_df,
                    x=category_column,
                    y=value_column,
                    title=f"{value_column} by {category_column}",
                    color=category_column,
                    color_discrete_sequence=CHART_COLORS,
                )

        if len(safe_df.columns) == 2 and len(numeric_columns) == 2:
            category_column = next((col for col in numeric_columns if safe_df[col].nunique(dropna=True) <= 12), None)
            value_column = next((col for col in numeric_columns if col != category_column), None)
            if category_column and value_column:
                chart_df = safe_df.copy()
                chart_df[category_column] = chart_df[category_column].astype(str)
                return px.bar(
                    chart_df,
                    x=category_column,
                    y=value_column,
                    color=category_column,
                    title=f"{value_column} by {category_column}",
                    color_discrete_sequence=CHART_COLORS,
                )

        if len(numeric_columns) >= 2:
            series_labels = _build_series_labels(safe_df.head(20), numeric_columns)
            preview = safe_df[numeric_columns[:8]].head(len(series_labels)).transpose().reset_index()
            preview.columns = ["metric"] + series_labels
            melted = preview.melt(id_vars="metric", var_name="series", value_name="value")
            return px.bar(
                melted,
                x="metric",
                y="value",
                color="series",
                barmode="group",
                title="Numeric comparison across returned rows",
                color_discrete_sequence=CHART_COLORS,
            )

        if categorical_columns:
            category_column = categorical_columns[0]
            counts = safe_df[category_column].astype(str).value_counts(dropna=False).head(10).reset_index()
            counts.columns = [category_column, "count"]
            return px.bar(
                counts,
                x=category_column,
                y="count",
                title=f"Frequency of {category_column}",
                color=category_column,
                color_discrete_sequence=CHART_COLORS,
            )
    except Exception:
        return _table_figure(df)

    return _table_figure(df)


def chart_to_payload(df: pd.DataFrame):
    chart = build_chart(df)

    chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font={"family": "Space Grotesk, sans-serif", "color": "#f5f7fb"},
        margin={"l": 30, "r": 20, "t": 60, "b": 30},
        legend={"title": {"text": "Series"}, "orientation": "v"},
    )
    chart.update_xaxes(gridcolor="rgba(255,255,255,0.08)")
    chart.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    return pio.to_json(chart)


def _empty_figure(message: str):
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 18},
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return figure


def _table_figure(df: pd.DataFrame):
    preview = df.head(12).fillna("").astype(str)
    figure = go.Figure(
        data=[
            go.Table(
                header={
                    "values": list(preview.columns),
                    "fill_color": "rgba(124, 240, 199, 0.14)",
                    "line_color": "rgba(255,255,255,0.08)",
                    "align": "left",
                    "font": {"color": "#f5f7fb", "family": "Space Grotesk, sans-serif", "size": 12},
                },
                cells={
                    "values": [preview[column].tolist() for column in preview.columns],
                    "fill_color": "rgba(255,255,255,0.02)",
                    "line_color": "rgba(255,255,255,0.06)",
                    "align": "left",
                    "font": {"color": "#dfe8f7", "family": "Space Grotesk, sans-serif", "size": 11},
                    "height": 30,
                },
            )
        ]
    )
    figure.update_layout(title="Result preview")
    return figure


def _build_series_labels(df: pd.DataFrame, numeric_columns: list[str]) -> list[str]:
    label_column = _pick_label_column(df, numeric_columns)
    if label_column:
        labels = df[label_column].astype(str).fillna("").tolist()
        cleaned = [label if label else f"Record {index + 1}" for index, label in enumerate(labels)]
        return _deduplicate_labels(cleaned)
    return [f"Record {index + 1}" for index in range(len(df.head(20)))]


def _pick_label_column(df: pd.DataFrame, numeric_columns: list[str]) -> str | None:
    for column in df.columns:
        if column in numeric_columns:
            if df[column].nunique(dropna=True) <= min(12, max(2, len(df))):
                return column
            continue
        if df[column].nunique(dropna=True) <= len(df):
            return column
    return None


def _deduplicate_labels(labels: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    deduplicated = []
    for label in labels:
        count = seen.get(label, 0) + 1
        seen[label] = count
        deduplicated.append(label if count == 1 else f"{label} ({count})")
    return deduplicated
