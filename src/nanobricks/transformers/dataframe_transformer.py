"""Enhanced DataFrame transformation nanobricks."""

from collections.abc import Callable
from typing import Any

from nanobricks.transformers.base import TransformerBase


class DataFrameOperator(TransformerBase[Any, Any]):
    """Performs operations on pandas DataFrames.

    This transformer provides a comprehensive set of DataFrame operations
    including filtering, grouping, aggregation, joining, and reshaping.
    """

    def __init__(self, *, operation: str, **kwargs: Any):
        """Initialize DataFrame operator.

        Args:
            operation: Operation to perform (filter, groupby, agg, merge, etc.)
            **kwargs: Operation-specific parameters
        """
        name = kwargs.pop("name", f"dataframe_{operation}")
        version = kwargs.pop("version", "1.0.0")
        super().__init__(name=name, version=version)

        # Check pandas availability
        try:
            import pandas as pd

            self._pd = pd
        except ImportError as e:
            msg = "pandas required. Install with: pip install pandas"
            raise ImportError(msg) from e

        self.operation = operation
        self.params = kwargs

    async def transform(self, input: Any) -> Any:
        """Apply DataFrame operation.

        Args:
            input: pandas DataFrame or data that can be converted to DataFrame

        Returns:
            Transformed DataFrame or result
        """
        # Ensure we have a DataFrame
        if not isinstance(input, self._pd.DataFrame):
            if isinstance(input, list) and all(isinstance(x, dict) for x in input):
                df = self._pd.DataFrame(input)
            elif isinstance(input, dict):
                df = self._pd.DataFrame([input])
            else:
                raise ValueError("Input must be DataFrame or list of dicts")
        else:
            df = input

        # Apply operation
        if self.operation == "filter":
            return self._filter(df)
        elif self.operation == "select":
            return self._select(df)
        elif self.operation == "groupby":
            return self._groupby(df)
        elif self.operation == "agg":
            return self._aggregate(df)
        elif self.operation == "sort":
            return self._sort(df)
        elif self.operation == "merge":
            return self._merge(df)
        elif self.operation == "pivot":
            return self._pivot(df)
        elif self.operation == "melt":
            return self._melt(df)
        elif self.operation == "dropna":
            return self._dropna(df)
        elif self.operation == "fillna":
            return self._fillna(df)
        elif self.operation == "apply":
            return self._apply(df)
        elif self.operation == "rolling":
            return self._rolling(df)
        elif self.operation == "resample":
            return self._resample(df)
        else:
            raise ValueError(f"Unknown operation: {self.operation}")

    def _filter(self, df: Any) -> Any:
        """Filter DataFrame rows."""
        query = self.params.get("query")
        if query:
            return df.query(query)

        condition = self.params.get("condition")
        if condition:
            return df[condition(df)]

        column = self.params.get("column")
        value = self.params.get("value")
        op = self.params.get("op", "==")

        if column and value is not None:
            if op == "==":
                return df[df[column] == value]
            elif op == "!=":
                return df[df[column] != value]
            elif op == ">":
                return df[df[column] > value]
            elif op == ">=":
                return df[df[column] >= value]
            elif op == "<":
                return df[df[column] < value]
            elif op == "<=":
                return df[df[column] <= value]
            elif op == "in":
                return df[df[column].isin(value)]
            elif op == "contains":
                return df[df[column].str.contains(value, na=False)]

        return df

    def _select(self, df: Any) -> Any:
        """Select columns."""
        columns = self.params.get("columns", [])
        if columns:
            return df[columns]
        return df

    def _groupby(self, df: Any) -> Any:
        """Group by columns."""
        by = self.params.get("by", [])
        agg = self.params.get("agg", {})

        if not by:
            raise ValueError("groupby requires 'by' parameter")

        grouped = df.groupby(by)

        if agg:
            return grouped.agg(agg).reset_index()

        return grouped

    def _aggregate(self, df: Any) -> Any:
        """Aggregate data."""
        agg_dict = self.params.get("agg", {})
        if agg_dict:
            return df.agg(agg_dict)

        func = self.params.get("func", "mean")
        return df.agg(func)

    def _sort(self, df: Any) -> Any:
        """Sort DataFrame."""
        by = self.params.get("by", [])
        ascending = self.params.get("ascending", True)

        if by:
            return df.sort_values(by=by, ascending=ascending)

        return df

    def _merge(self, df: Any) -> Any:
        """Merge with another DataFrame."""
        other = self.params.get("other")
        if other is None:
            raise ValueError("merge requires 'other' DataFrame")

        how = self.params.get("how", "inner")
        on = self.params.get("on")
        left_on = self.params.get("left_on")
        right_on = self.params.get("right_on")

        return df.merge(other, how=how, on=on, left_on=left_on, right_on=right_on)

    def _pivot(self, df: Any) -> Any:
        """Pivot DataFrame."""
        index = self.params.get("index")
        columns = self.params.get("columns")
        values = self.params.get("values")
        aggfunc = self.params.get("aggfunc", "mean")

        return df.pivot_table(
            index=index, columns=columns, values=values, aggfunc=aggfunc
        ).reset_index()

    def _melt(self, df: Any) -> Any:
        """Melt DataFrame from wide to long format."""
        id_vars = self.params.get("id_vars")
        value_vars = self.params.get("value_vars")
        var_name = self.params.get("var_name", "variable")
        value_name = self.params.get("value_name", "value")

        return df.melt(
            id_vars=id_vars,
            value_vars=value_vars,
            var_name=var_name,
            value_name=value_name,
        )

    def _dropna(self, df: Any) -> Any:
        """Drop missing values."""
        axis = self.params.get("axis", 0)
        how = self.params.get("how", "any")
        subset = self.params.get("subset")

        return df.dropna(axis=axis, how=how, subset=subset)

    def _fillna(self, df: Any) -> Any:
        """Fill missing values."""
        value = self.params.get("value")
        method = self.params.get("method")

        if value is not None:
            return df.fillna(value)
        elif method:
            return df.fillna(method=method)

        return df

    def _apply(self, df: Any) -> Any:
        """Apply function to DataFrame."""
        func = self.params.get("func")
        axis = self.params.get("axis", 0)

        if not func:
            raise ValueError("apply requires 'func' parameter")

        return df.apply(func, axis=axis)

    def _rolling(self, df: Any) -> Any:
        """Apply rolling window operations."""
        window = self.params.get("window", 3)
        func = self.params.get("func", "mean")
        center = self.params.get("center", False)

        rolling = df.rolling(window=window, center=center)

        if isinstance(func, str):
            return getattr(rolling, func)()
        else:
            return rolling.apply(func)

    def _resample(self, df: Any) -> Any:
        """Resample time series data."""
        rule = self.params.get("rule", "D")
        func = self.params.get("func", "mean")

        # Ensure datetime index
        if not isinstance(df.index, self._pd.DatetimeIndex):
            date_col = self.params.get("date_column")
            if date_col:
                df = df.set_index(self._pd.to_datetime(df[date_col]))
            else:
                raise ValueError("resample requires datetime index or date_column")

        resampled = df.resample(rule)

        if isinstance(func, str):
            return getattr(resampled, func)()
        else:
            return resampled.apply(func)


class DataFrameFilter(DataFrameOperator):
    """Specialized DataFrame filter transformer."""

    def __init__(
        self,
        *,
        query: str | None = None,
        column: str | None = None,
        value: Any = None,
        op: str = "==",
        condition: Callable | None = None,
        name: str = "dataframe_filter",
        version: str = "1.0.0",
    ):
        """Initialize filter.

        Args:
            query: pandas query string
            column: Column to filter
            value: Value to compare
            op: Comparison operator
            condition: Custom filter function
            name: Transformer name
            version: Transformer version
        """
        super().__init__(
            operation="filter",
            query=query,
            column=column,
            value=value,
            op=op,
            condition=condition,
            name=name,
            version=version,
        )


class DataFrameGroupBy(DataFrameOperator):
    """Specialized DataFrame groupby transformer."""

    def __init__(
        self,
        *,
        by: str | list[str],
        agg: dict[str, str | list[str]] | None = None,
        name: str = "dataframe_groupby",
        version: str = "1.0.0",
    ):
        """Initialize groupby.

        Args:
            by: Column(s) to group by
            agg: Aggregation specification
            name: Transformer name
            version: Transformer version
        """
        if isinstance(by, str):
            by = [by]

        super().__init__(
            operation="groupby", by=by, agg=agg or {}, name=name, version=version
        )


class DataFrameMerge(DataFrameOperator):
    """Specialized DataFrame merge transformer."""

    def __init__(
        self,
        *,
        other: Any,
        how: str = "inner",
        on: str | list[str] | None = None,
        left_on: str | list[str] | None = None,
        right_on: str | list[str] | None = None,
        name: str = "dataframe_merge",
        version: str = "1.0.0",
    ):
        """Initialize merge.

        Args:
            other: DataFrame to merge with
            how: Join type (inner, outer, left, right)
            on: Column(s) to join on
            left_on: Left DataFrame column(s)
            right_on: Right DataFrame column(s)
            name: Transformer name
            version: Transformer version
        """
        super().__init__(
            operation="merge",
            other=other,
            how=how,
            on=on,
            left_on=left_on,
            right_on=right_on,
            name=name,
            version=version,
        )


class DataFrameReshape(DataFrameOperator):
    """Specialized DataFrame reshape transformer."""

    def __init__(self, *, reshape_type: str = "pivot", **kwargs: Any):
        """Initialize reshape.

        Args:
            reshape_type: Type of reshape (pivot, melt)
            **kwargs: Reshape-specific parameters
        """
        name = kwargs.pop("name", f"dataframe_{reshape_type}")
        version = kwargs.pop("version", "1.0.0")

        super().__init__(operation=reshape_type, name=name, version=version, **kwargs)


class DataFrameTimeSeriesOperator(DataFrameOperator):
    """Specialized time series DataFrame transformer."""

    def __init__(self, *, operation: str = "resample", **kwargs: Any):
        """Initialize time series operator.

        Args:
            operation: Time series operation (resample, rolling)
            **kwargs: Operation-specific parameters
        """
        name = kwargs.pop("name", f"dataframe_{operation}")
        version = kwargs.pop("version", "1.0.0")

        super().__init__(operation=operation, name=name, version=version, **kwargs)
