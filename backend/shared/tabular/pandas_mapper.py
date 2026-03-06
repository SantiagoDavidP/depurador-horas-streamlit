from __future__ import annotations

from typing import Any

import pandas as pd

from backend.application.tabular.table_data import TableData


def from_pandas_table(df: pd.DataFrame) -> TableData:
    rows = tuple(tuple(row) for row in df.itertuples(index=False, name=None))
    return TableData(
        columns=tuple(df.columns.tolist()),
        rows=rows,
        attrs=dict(getattr(df, "attrs", {}) or {}),
    )


def to_pandas_table(table: Any) -> pd.DataFrame:
    if isinstance(table, pd.DataFrame):
        return table.copy()
    if isinstance(table, TableData):
        dataframe = pd.DataFrame(list(table.rows), columns=list(table.columns))
        dataframe.attrs.update(dict(table.attrs or {}))
        return dataframe
    raise TypeError(f"Unsupported tabular value: {type(table)!r}")
