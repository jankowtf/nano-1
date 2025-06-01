"""Tests for DataFrame transformers."""

from typing import Any

import pytest

from nanobricks.transformers.dataframe_transformer import (
    DataFrameFilter,
    DataFrameGroupBy,
    DataFrameMerge,
    DataFrameOperator,
    DataFrameReshape,
    DataFrameTimeSeriesOperator,
)

# Skip tests if pandas not available
pytest.importorskip("pandas")
import pandas as pd


class TestDataFrameOperator:
    """Test DataFrameOperator."""

    @pytest.fixture
    def sample_data(self) -> list[dict[str, Any]]:
        """Sample data for testing."""
        return [
            {"name": "Alice", "age": 30, "city": "New York", "score": 85},
            {"name": "Bob", "age": 25, "city": "London", "score": 90},
            {"name": "Charlie", "age": 35, "city": "New York", "score": 78},
            {"name": "David", "age": 28, "city": "London", "score": 92},
            {"name": "Eve", "age": 32, "city": "Paris", "score": 88},
        ]

    @pytest.fixture
    def sample_df(self, sample_data) -> pd.DataFrame:
        """Sample DataFrame for testing."""
        return pd.DataFrame(sample_data)

    async def test_filter_by_query(self, sample_data):
        """Test filtering with query string."""
        operator = DataFrameOperator(operation="filter", query="age > 30")
        result = await operator.invoke(sample_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert all(result["age"] > 30)

    async def test_filter_by_column_value(self, sample_data):
        """Test filtering by column and value."""
        operator = DataFrameOperator(operation="filter", column="city", value="London")
        result = await operator.invoke(sample_data)

        assert len(result) == 2
        assert all(result["city"] == "London")

    async def test_filter_with_operators(self, sample_data):
        """Test filtering with different operators."""
        # Greater than
        operator = DataFrameOperator(
            operation="filter", column="score", value=85, op=">"
        )
        result = await operator.invoke(sample_data)
        assert all(result["score"] > 85)

        # In operator
        operator = DataFrameOperator(
            operation="filter", column="city", value=["New York", "Paris"], op="in"
        )
        result = await operator.invoke(sample_data)
        assert all(result["city"].isin(["New York", "Paris"]))

    async def test_select_columns(self, sample_data):
        """Test column selection."""
        operator = DataFrameOperator(operation="select", columns=["name", "score"])
        result = await operator.invoke(sample_data)

        assert list(result.columns) == ["name", "score"]
        assert len(result) == len(sample_data)

    async def test_groupby_aggregate(self, sample_data):
        """Test groupby with aggregation."""
        operator = DataFrameOperator(
            operation="groupby",
            by=["city"],
            agg={"age": "mean", "score": ["mean", "max"]},
        )
        result = await operator.invoke(sample_data)

        assert "city" in result.columns
        assert len(result) == 3  # Three unique cities

    async def test_sort(self, sample_data):
        """Test sorting."""
        operator = DataFrameOperator(operation="sort", by=["score"], ascending=False)
        result = await operator.invoke(sample_data)

        scores = result["score"].tolist()
        assert scores == sorted(scores, reverse=True)

    async def test_dropna(self):
        """Test dropping missing values."""
        data = [
            {"a": 1, "b": 2},
            {"a": None, "b": 3},
            {"a": 4, "b": None},
        ]

        operator = DataFrameOperator(operation="dropna")
        result = await operator.invoke(data)

        assert len(result) == 1
        assert result.iloc[0]["a"] == 1

    async def test_fillna(self):
        """Test filling missing values."""
        data = [
            {"a": 1, "b": None},
            {"a": None, "b": 3},
        ]

        operator = DataFrameOperator(operation="fillna", value=0)
        result = await operator.invoke(data)

        assert result.iloc[0]["b"] == 0
        assert result.iloc[1]["a"] == 0

    async def test_apply_function(self, sample_data):
        """Test applying a function."""

        def double_score(row):
            row["score"] = row["score"] * 2
            return row

        operator = DataFrameOperator(operation="apply", func=double_score, axis=1)
        result = await operator.invoke(sample_data)

        original_df = pd.DataFrame(sample_data)
        assert all(result["score"] == original_df["score"] * 2)


class TestDataFrameFilter:
    """Test DataFrameFilter."""

    async def test_filter_basic(self):
        """Test basic filtering."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 35},
        ]

        filter = DataFrameFilter(column="age", value=30, op=">=")
        result = await filter.invoke(data)

        assert len(result) == 2
        assert all(result["age"] >= 30)

    async def test_filter_query(self):
        """Test query-based filtering."""
        data = [
            {"name": "Alice", "score": 85, "grade": "A"},
            {"name": "Bob", "score": 75, "grade": "B"},
            {"name": "Charlie", "score": 90, "grade": "A"},
        ]

        filter = DataFrameFilter(query="score > 80 and grade == 'A'")
        result = await filter.invoke(data)

        assert len(result) == 2
        assert all((result["score"] > 80) & (result["grade"] == "A"))

    async def test_filter_custom_condition(self):
        """Test custom condition filtering."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 35},
        ]

        def is_eligible(df):
            return (df["age"] >= 25) & (df["age"] <= 30)

        filter = DataFrameFilter(condition=is_eligible)
        result = await filter.invoke(data)

        assert len(result) == 2
        assert all((result["age"] >= 25) & (result["age"] <= 30))


class TestDataFrameGroupBy:
    """Test DataFrameGroupBy."""

    async def test_groupby_single_column(self):
        """Test grouping by single column."""
        data = [
            {"category": "A", "value": 10},
            {"category": "B", "value": 20},
            {"category": "A", "value": 15},
            {"category": "B", "value": 25},
        ]

        groupby = DataFrameGroupBy(by="category", agg={"value": "sum"})
        result = await groupby.invoke(data)

        assert len(result) == 2
        assert result[result["category"] == "A"]["value"].iloc[0] == 25
        assert result[result["category"] == "B"]["value"].iloc[0] == 45

    async def test_groupby_multiple_columns(self):
        """Test grouping by multiple columns."""
        data = [
            {"city": "NY", "year": 2020, "sales": 100},
            {"city": "NY", "year": 2021, "sales": 120},
            {"city": "LA", "year": 2020, "sales": 90},
            {"city": "LA", "year": 2021, "sales": 110},
        ]

        groupby = DataFrameGroupBy(by=["city", "year"], agg={"sales": "sum"})
        result = await groupby.invoke(data)

        assert len(result) == 4
        assert "city" in result.columns
        assert "year" in result.columns

    async def test_groupby_multiple_aggregations(self):
        """Test multiple aggregations."""
        data = [
            {"category": "A", "price": 10, "quantity": 5},
            {"category": "A", "price": 15, "quantity": 3},
            {"category": "B", "price": 20, "quantity": 2},
            {"category": "B", "price": 25, "quantity": 4},
        ]

        groupby = DataFrameGroupBy(
            by="category", agg={"price": ["mean", "max"], "quantity": "sum"}
        )
        result = await groupby.invoke(data)

        assert len(result) == 2
        # Check column names after aggregation
        assert ("price", "mean") in result.columns or "price_mean" in result.columns


class TestDataFrameMerge:
    """Test DataFrameMerge."""

    async def test_merge_inner(self):
        """Test inner merge."""
        left_data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]

        right_data = pd.DataFrame(
            [
                {"id": 1, "score": 85},
                {"id": 2, "score": 90},
                {"id": 4, "score": 95},
            ]
        )

        merge = DataFrameMerge(other=right_data, how="inner", on="id")
        result = await merge.invoke(left_data)

        assert len(result) == 2  # Only matching IDs
        assert "name" in result.columns
        assert "score" in result.columns

    async def test_merge_left(self):
        """Test left merge."""
        left_data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

        right_data = pd.DataFrame(
            [
                {"id": 1, "score": 85},
                {"id": 3, "score": 90},
            ]
        )

        merge = DataFrameMerge(other=right_data, how="left", on="id")
        result = await merge.invoke(left_data)

        assert len(result) == 2  # All left records
        assert pd.isna(result[result["id"] == 2]["score"].iloc[0])

    async def test_merge_different_keys(self):
        """Test merge with different column names."""
        left_data = [
            {"user_id": 1, "name": "Alice"},
            {"user_id": 2, "name": "Bob"},
        ]

        right_data = pd.DataFrame(
            [
                {"uid": 1, "department": "Sales"},
                {"uid": 2, "department": "IT"},
            ]
        )

        merge = DataFrameMerge(
            other=right_data, how="inner", left_on="user_id", right_on="uid"
        )
        result = await merge.invoke(left_data)

        assert len(result) == 2
        assert "department" in result.columns


class TestDataFrameReshape:
    """Test DataFrameReshape."""

    async def test_pivot(self):
        """Test pivot operation."""
        data = [
            {"date": "2024-01", "product": "A", "sales": 100},
            {"date": "2024-01", "product": "B", "sales": 150},
            {"date": "2024-02", "product": "A", "sales": 120},
            {"date": "2024-02", "product": "B", "sales": 180},
        ]

        reshape = DataFrameReshape(
            reshape_type="pivot",
            index="date",
            columns="product",
            values="sales",
            aggfunc="sum",
        )
        result = await reshape.invoke(data)

        assert "date" in result.columns
        assert "A" in result.columns or "product_A" in result.columns
        assert len(result) == 2  # Two dates

    async def test_melt(self):
        """Test melt operation."""
        data = [
            {"id": 1, "jan": 100, "feb": 120, "mar": 130},
            {"id": 2, "jan": 200, "feb": 220, "mar": 230},
        ]

        reshape = DataFrameReshape(
            reshape_type="melt",
            id_vars="id",
            value_vars=["jan", "feb", "mar"],
            var_name="month",
            value_name="amount",
        )
        result = await reshape.invoke(data)

        assert len(result) == 6  # 2 ids * 3 months
        assert "month" in result.columns
        assert "amount" in result.columns


class TestDataFrameTimeSeriesOperator:
    """Test DataFrameTimeSeriesOperator."""

    async def test_rolling_window(self):
        """Test rolling window operations."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10, freq="D"),
                "value": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            }
        )

        operator = DataFrameTimeSeriesOperator(
            operation="rolling", window=3, func="mean"
        )
        result = await operator.invoke(data)

        # First two values should be NaN (window size 3)
        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        # Third value should be mean of first 3
        assert result["value"].iloc[2] == 2.0

    async def test_resample(self):
        """Test resampling time series data."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10, freq="D"),
                "value": range(10),
            }
        )

        operator = DataFrameTimeSeriesOperator(
            operation="resample",
            rule="W",  # Weekly
            func="sum",
            date_column="date",
        )
        result = await operator.invoke(data)

        # Should have fewer rows after weekly resampling
        assert len(result) < len(data)
        assert isinstance(result.index, pd.DatetimeIndex)
