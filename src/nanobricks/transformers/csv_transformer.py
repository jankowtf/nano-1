"""CSV transformation nanobricks."""

import csv
import io
from typing import Any

from nanobricks.transformers.base import TransformerBase


class CSVParser(TransformerBase[str, list[dict[str, str]]]):
    """Parses CSV text into list of dictionaries."""

    def __init__(
        self,
        *,
        delimiter: str = ",",
        quotechar: str = '"',
        skip_empty: bool = True,
        strip_values: bool = True,
        skip_rows: int = 0,
        max_rows: int | None = None,
        name: str = "csv_parser",
        version: str = "1.0.0",
    ):
        """Initialize CSV parser.

        Args:
            delimiter: Field delimiter
            quotechar: Quote character
            skip_empty: Skip empty rows
            strip_values: Strip whitespace from values
            skip_rows: Number of header rows to skip
            max_rows: Maximum rows to parse
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.skip_empty = skip_empty
        self.strip_values = strip_values
        self.skip_rows = skip_rows
        self.max_rows = max_rows

    async def transform(self, input: str) -> list[dict[str, str]]:
        """Parse CSV text.

        Args:
            input: CSV text

        Returns:
            List of row dictionaries
        """
        reader = csv.DictReader(
            io.StringIO(input), delimiter=self.delimiter, quotechar=self.quotechar
        )

        # Skip initial rows
        for _ in range(self.skip_rows):
            next(reader, None)

        rows = []
        for i, row in enumerate(reader):
            if self.max_rows and i >= self.max_rows:
                break

            # Skip empty rows
            if self.skip_empty and not any(row.values()):
                continue

            # Strip values if requested
            if self.strip_values:
                row = {
                    k: v.strip() if isinstance(v, str) else v for k, v in row.items()
                }

            rows.append(row)

        return rows


class CSVSerializer(TransformerBase[list[dict[str, Any]], str]):
    """Serializes list of dictionaries to CSV."""

    def __init__(
        self,
        *,
        delimiter: str = ",",
        quotechar: str = '"',
        include_header: bool = True,
        columns: list[str] | None = None,
        name: str = "csv_serializer",
        version: str = "1.0.0",
    ):
        """Initialize CSV serializer.

        Args:
            delimiter: Field delimiter
            quotechar: Quote character
            include_header: Include header row
            columns: Column names (auto-detected if None)
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.include_header = include_header
        self.columns = columns

    async def transform(self, input: list[dict[str, Any]]) -> str:
        """Serialize to CSV.

        Args:
            input: List of dictionaries

        Returns:
            CSV text
        """
        if not input:
            return ""

        # Determine columns
        if self.columns:
            fieldnames = self.columns
        else:
            # Collect all unique keys
            fieldnames = []
            seen = set()
            for row in input:
                for key in row.keys():
                    if key not in seen:
                        fieldnames.append(key)
                        seen.add(key)

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self.delimiter,
            quotechar=self.quotechar,
            extrasaction="ignore",
        )

        if self.include_header:
            writer.writeheader()

        writer.writerows(input)
        return output.getvalue()


class DataFrameTransformer(TransformerBase[list[dict] | str, Any]):
    """Transforms data to/from pandas DataFrame.

    Requires pandas to be installed.
    """

    def __init__(
        self,
        *,
        input_format: str = "records",
        output_format: str = "dataframe",
        parse_dates: list[str] | None = None,
        index_col: str | None = None,
        dtype: dict[str, type] | None = None,
        name: str = "dataframe_transformer",
        version: str = "1.0.0",
    ):
        """Initialize DataFrame transformer.

        Args:
            input_format: Input format (records, csv, json)
            output_format: Output format (dataframe, records, csv, json, html)
            parse_dates: Columns to parse as dates
            index_col: Column to use as index
            dtype: Column data types
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)

        # Check pandas availability
        try:
            import pandas as pd

            self._pd = pd
        except ImportError as e:
            raise ImportError(
                "pandas required. Install with: pip install pandas"
            ) from e

        self.input_format = input_format
        self.output_format = output_format
        self.parse_dates = parse_dates
        self.index_col = index_col
        self.dtype = dtype

    async def transform(self, input: list[dict] | str) -> Any:
        """Transform to/from DataFrame.

        Args:
            input: Input data

        Returns:
            Transformed data
        """
        # Parse input to DataFrame
        if self.input_format == "records":
            df = self._pd.DataFrame(input)
        elif self.input_format == "csv":
            df = self._pd.read_csv(
                io.StringIO(input),
                parse_dates=self.parse_dates,
                index_col=self.index_col,
                dtype=self.dtype,
            )
        elif self.input_format == "json":
            df = self._pd.read_json(
                io.StringIO(input), orient="records", dtype=self.dtype
            )
        else:
            raise ValueError(f"Unknown input format: {self.input_format}")

        # Convert output
        if self.output_format == "dataframe":
            return df
        elif self.output_format == "records":
            return df.to_dict(orient="records")
        elif self.output_format == "csv":
            return df.to_csv(index=False)
        elif self.output_format == "json":
            return df.to_json(orient="records")
        elif self.output_format == "html":
            return df.to_html(index=False)
        else:
            raise ValueError(f"Unknown output format: {self.output_format}")


class PivotTransformer(TransformerBase[list[dict[str, Any]], list[dict[str, Any]]]):
    """Pivots data based on specified columns.

    Requires pandas for complex pivoting.
    """

    def __init__(
        self,
        *,
        index: str | list[str],
        columns: str | list[str],
        values: str | list[str],
        aggfunc: str = "sum",
        fill_value: Any = None,
        name: str = "pivot_transformer",
        version: str = "1.0.0",
    ):
        """Initialize pivot transformer.

        Args:
            index: Column(s) to use as index
            columns: Column(s) to pivot
            values: Column(s) to aggregate
            aggfunc: Aggregation function (sum, mean, count, etc.)
            fill_value: Value to fill missing data
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)

        try:
            import pandas as pd

            self._pd = pd
        except ImportError as e:
            raise ImportError("pandas required for pivot operations") from e

        self.index = index
        self.columns = columns
        self.values = values
        self.aggfunc = aggfunc
        self.fill_value = fill_value

    async def transform(self, input: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pivot the data.

        Args:
            input: List of records

        Returns:
            Pivoted data as list of records
        """
        df = self._pd.DataFrame(input)

        # Perform pivot
        pivoted = df.pivot_table(
            index=self.index,
            columns=self.columns,
            values=self.values,
            aggfunc=self.aggfunc,
            fill_value=self.fill_value,
        )

        # Flatten multi-level columns if necessary
        if isinstance(pivoted.columns, self._pd.MultiIndex):
            pivoted.columns = [
                "_".join(map(str, col)).strip() for col in pivoted.columns.values
            ]

        # Reset index to convert back to records
        pivoted = pivoted.reset_index()

        return pivoted.to_dict(orient="records")
