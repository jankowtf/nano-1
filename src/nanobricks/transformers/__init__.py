"""Transformer nanobricks for data transformation."""

from nanobricks.transformers.aggregate_transformer import (
    AverageTransformer,
    CountTransformer,
    FrequencyTransformer,
    JoinTransformer,
    MaxTransformer,
    MinTransformer,
    ReduceTransformer,
    SumTransformer,
)
from nanobricks.transformers.base import TransformerBase, TransformerBrick
from nanobricks.transformers.case_transformer import (
    CamelCaseTransformer,
    KebabCaseTransformer,
    PascalCaseTransformer,
    SnakeCaseTransformer,
    TitleCaseTransformer,
    UpperCaseTransformer,
)
from nanobricks.transformers.csv_transformer import (
    CSVParser,
    CSVSerializer,
    DataFrameTransformer,
    PivotTransformer,
)
from nanobricks.transformers.dataframe_transformer import (
    DataFrameFilter,
    DataFrameGroupBy,
    DataFrameMerge,
    DataFrameOperator,
    DataFrameReshape,
    DataFrameTimeSeriesOperator,
)
from nanobricks.transformers.filter_transformer import (
    FilterTransformer,
    RemoveDuplicatesTransformer,
    RemoveNoneTransformer,
    SkipTransformer,
    TakeTransformer,
)
from nanobricks.transformers.json_transformer import (
    JSONParser,
    JSONPrettyPrinter,
    JSONSerializer,
)
from nanobricks.transformers.map_transformer import (
    FlatMapTransformer,
    GroupByTransformer,
    MapTransformer,
    SelectTransformer,
    ZipTransformer,
)
from nanobricks.transformers.text_normalizer import (
    SentenceNormalizer,
    TextNormalizer,
    TokenNormalizer,
)
from nanobricks.transformers.type_converter import (
    BulkTypeConverter,
    DynamicTypeConverter,
    SmartTypeConverter,
)

__all__ = [
    # Base
    "TransformerBrick",
    "TransformerBase",
    # JSON
    "JSONParser",
    "JSONSerializer",
    "JSONPrettyPrinter",
    # Case
    "SnakeCaseTransformer",
    "CamelCaseTransformer",
    "PascalCaseTransformer",
    "KebabCaseTransformer",
    "UpperCaseTransformer",
    "TitleCaseTransformer",
    # Filter
    "FilterTransformer",
    "RemoveNoneTransformer",
    "RemoveDuplicatesTransformer",
    "TakeTransformer",
    "SkipTransformer",
    # Map
    "MapTransformer",
    "SelectTransformer",
    "FlatMapTransformer",
    "GroupByTransformer",
    "ZipTransformer",
    # Aggregate
    "SumTransformer",
    "AverageTransformer",
    "MinTransformer",
    "MaxTransformer",
    "CountTransformer",
    "ReduceTransformer",
    "JoinTransformer",
    "FrequencyTransformer",
    # CSV
    "CSVParser",
    "CSVSerializer",
    "DataFrameTransformer",
    "PivotTransformer",
    # DataFrame Operations
    "DataFrameOperator",
    "DataFrameFilter",
    "DataFrameGroupBy",
    "DataFrameMerge",
    "DataFrameReshape",
    "DataFrameTimeSeriesOperator",
    # Text
    "TextNormalizer",
    "TokenNormalizer",
    "SentenceNormalizer",
    # Type
    "SmartTypeConverter",
    "BulkTypeConverter",
    "DynamicTypeConverter",
]
