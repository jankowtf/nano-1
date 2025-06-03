"""Examples of advanced transformers in nanobricks."""

import asyncio
from typing import List, Dict, Any

from nanobricks import Pipeline
from nanobricks.transformers import (
    CSVParser,
    CSVSerializer,
    TextNormalizer,
    TokenNormalizer,
    SentenceNormalizer,
    SmartTypeConverter,
    BulkTypeConverter,
    DynamicTypeConverter,
    JSONSerializer,
    GroupByTransformer,
    AverageTransformer,
    DataFrameOperator,
    DataFrameFilter,
    DataFrameGroupBy,
    DataFrameMerge,
    DataFrameReshape,
)


async def demo_csv_processing():
    """Demonstrate CSV processing capabilities."""
    print("\n=== CSV Processing Demo ===\n")
    
    # Sample CSV data
    csv_data = """product,category,price,quantity,date
iPhone 14,Electronics,999.99,50,2024-01-15
MacBook Pro,Electronics,2499.00,20,2024-01-16
Coffee Maker,Appliances,79.99,100,2024-01-15
Wireless Mouse,Electronics,29.99,200,2024-01-17
Blender,Appliances,49.99,75,2024-01-16"""
    
    # Parse CSV
    parser = CSVParser(strip_values=True)
    records = await parser.transform(csv_data)
    print(f"Parsed {len(records)} records from CSV")
    
    # Convert types
    type_converter = DynamicTypeConverter(
        type_map={
            "price": float,
            "quantity": int,
            "date": str  # Keep as string for now
        }
    )
    
    typed_records = []
    for record in records:
        typed = await type_converter.transform(record)
        typed_records.append(typed)
    
    print(f"\nFirst record: {typed_records[0]}")
    print(f"  Price type: {type(typed_records[0]['price'])}")
    print(f"  Quantity type: {type(typed_records[0]['quantity'])}")
    
    # Group by category
    grouper = GroupByTransformer(key_func=lambda x: x["category"])
    grouped = await grouper.transform(typed_records)
    
    print(f"\nProducts by category:")
    for category, products in grouped.items():
        total_value = sum(p["price"] * p["quantity"] for p in products)
        print(f"  {category}: {len(products)} products, ${total_value:,.2f} total value")
    
    # Export subset as CSV
    electronics = grouped["Electronics"]
    serializer = CSVSerializer(columns=["product", "price", "quantity"])
    electronics_csv = await serializer.transform(electronics)
    
    print(f"\nElectronics CSV export:")
    print(electronics_csv)


async def demo_text_normalization():
    """Demonstrate text normalization capabilities."""
    print("\n=== Text Normalization Demo ===\n")
    
    # Sample messy text
    messy_text = """
    URGENT: Don't forget to check out our AMAZING deals at https://shop.example.com!!! 
    
    Contact us at support@example.com or call 1-800-SHOP-NOW (1-800-746-7669).
    
    We're offering 50% OFF on selected items. That's right - HALF PRICE!
    
    CEO John Smith says: "It's the best time to buy. You won't regret it!"
    """
    
    # Basic normalization
    basic_normalizer = TextNormalizer(
        lowercase=True,
        remove_extra_spaces=True
    )
    
    basic_result = await basic_normalizer.transform(messy_text)
    print("Basic normalization:")
    print(f"  Length: {len(messy_text)} -> {len(basic_result)}")
    print(f"  Preview: {basic_result[:100]}...")
    
    # Aggressive normalization
    aggressive_normalizer = TextNormalizer(
        lowercase=True,
        remove_punctuation=True,
        remove_numbers=True,
        remove_urls=True,
        remove_emails=True,
        remove_extra_spaces=True,
        expand_contractions=True,
        custom_replacements={"ceo": "chief executive officer"}
    )
    
    aggressive_result = await aggressive_normalizer.transform(messy_text)
    print("\nAggressive normalization:")
    print(f"  Length: {len(messy_text)} -> {len(aggressive_result)}")
    print(f"  Result: {aggressive_result}")
    
    # Sentence extraction
    sentence_normalizer = SentenceNormalizer(
        min_length=20,
        strip_sentences=True
    )
    
    sentences = await sentence_normalizer.transform(messy_text)
    print(f"\nExtracted {len(sentences)} meaningful sentences:")
    for i, sentence in enumerate(sentences, 1):
        print(f"  {i}. {sentence}")


async def demo_smart_type_conversion():
    """Demonstrate smart type conversion."""
    print("\n=== Smart Type Conversion Demo ===\n")
    
    # Mixed data that needs conversion
    raw_data = {
        "user_id": "12345",
        "age": "28",
        "salary": "$75,000.50",
        "is_active": "true",
        "join_date": "2023-06-15",
        "scores": "[85, 92, 78, 94]",
        "preferences": '{"theme": "dark", "notifications": true}',
        "rating": "4.5",
        "verified": "yes"
    }
    
    # Define converters for each field
    converters = {
        "user_id": SmartTypeConverter(target_type=int),
        "age": SmartTypeConverter(target_type=int),
        "salary": SmartTypeConverter(
            target_type=float,
            custom_converters={
                str: lambda x: float(x.replace("$", "").replace(",", ""))
            }
        ),
        "is_active": SmartTypeConverter(target_type=bool),
        "join_date": SmartTypeConverter(
            target_type=str  # Keep as string for simplicity
        ),
        "scores": SmartTypeConverter(target_type=list),
        "preferences": SmartTypeConverter(target_type=dict),
        "rating": SmartTypeConverter(target_type=float),
        "verified": SmartTypeConverter(target_type=bool)
    }
    
    # Convert each field
    converted = {}
    for field, value in raw_data.items():
        if field in converters:
            converted[field] = await converters[field].transform(value)
        else:
            converted[field] = value
    
    print("Converted data:")
    for field, value in converted.items():
        print(f"  {field}: {value} ({type(value).__name__})")
    
    # Calculate average score
    avg_transformer = AverageTransformer()
    avg_score = await avg_transformer.transform(converted["scores"])
    print(f"\nAverage score: {avg_score:.1f}")


async def demo_data_pipeline():
    """Demonstrate a complete data processing pipeline."""
    print("\n=== Data Processing Pipeline Demo ===\n")
    
    # Raw survey responses
    survey_csv = """respondent_id,age,satisfaction,comments,recommended
R001,25,4,"Great service, but the website could be better.",yes
R002,32,5,EXCELLENT! Will definitely come back!!!,TRUE
R003,45,2,"Not happy. Too expensive and slow delivery.",no
R004,28,4,"Good overall. Fast shipping.",1
R005,55,3,"It's okay. Nothing special.",false
R006,19,5,"Amazing! Best purchase ever! 💯",yes
R007,38,1,"Terrible experience. Never again.",0
R008,42,4,"Pretty good, would recommend to friends",true"""
    
    # Build processing pipeline
    from nanobricks import Nanobrick
    
    class SentimentAnalyzer(Nanobrick[Dict[str, Any], Dict[str, Any]]):
        """Simple sentiment analysis based on satisfaction score."""
        
        async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
            result = input.copy()
            
            score = int(input.get("satisfaction", 0))
            if score >= 4:
                sentiment = "positive"
            elif score == 3:
                sentiment = "neutral"
            else:
                sentiment = "negative"
            
            result["sentiment"] = sentiment
            return result
    
    # Create pipeline components
    csv_parser = CSVParser()
    
    # Type converter for the data
    type_converter = BulkTypeConverter(
        target_type=dict,
        skip_errors=False
    )
    
    # Text normalizer for comments
    comment_normalizer = TextNormalizer(
        lowercase=True,
        remove_punctuation=False,
        remove_extra_spaces=True
    )
    
    # Process the data
    print("Processing survey responses...")
    
    # 1. Parse CSV
    records = await csv_parser.transform(survey_csv)
    print(f"  ✓ Parsed {len(records)} responses")
    
    # 2. Convert types and normalize
    processed_records = []
    bool_converter = SmartTypeConverter(target_type=bool)
    int_converter = SmartTypeConverter(target_type=int)
    
    for record in records:
        # Convert age to int
        record["age"] = await int_converter.transform(record["age"])
        
        # Convert satisfaction to int
        record["satisfaction"] = await int_converter.transform(record["satisfaction"])
        
        # Convert recommended to bool
        record["recommended"] = await bool_converter.transform(record["recommended"])
        
        # Normalize comments
        record["comments"] = await comment_normalizer.transform(record["comments"])
        
        processed_records.append(record)
    
    print("  ✓ Converted types and normalized text")
    
    # 3. Analyze sentiment
    analyzer = SentimentAnalyzer()
    analyzed = []
    for record in processed_records:
        result = await analyzer.invoke(record)
        analyzed.append(result)
    
    print("  ✓ Analyzed sentiment")
    
    # 4. Group by sentiment
    grouper = GroupByTransformer(key_func=lambda x: x["sentiment"])
    grouped = await grouper.transform(analyzed)
    
    # 5. Generate summary
    print("\nSurvey Summary:")
    print(f"  Total responses: {len(analyzed)}")
    
    for sentiment, responses in grouped.items():
        avg_age = sum(r["age"] for r in responses) / len(responses)
        recommend_rate = sum(1 for r in responses if r["recommended"]) / len(responses) * 100
        
        print(f"\n  {sentiment.upper()} ({len(responses)} responses):")
        print(f"    - Average age: {avg_age:.1f}")
        print(f"    - Recommendation rate: {recommend_rate:.0f}%")
        
        # Sample comment
        if responses:
            print(f"    - Sample comment: \"{responses[0]['comments'][:50]}...\"")
    
    # 6. Export summary as CSV
    summary_data = []
    for sentiment, responses in grouped.items():
        summary_data.append({
            "sentiment": sentiment,
            "count": len(responses),
            "avg_satisfaction": sum(r["satisfaction"] for r in responses) / len(responses),
            "recommendation_rate": sum(1 for r in responses if r["recommended"]) / len(responses)
        })
    
    serializer = CSVSerializer()
    summary_csv = await serializer.transform(summary_data)
    
    print("\nSummary CSV:")
    print(summary_csv)


async def demo_advanced_text_processing():
    """Demonstrate advanced text processing with tokens and sentences."""
    print("\n=== Advanced Text Processing Demo ===\n")
    
    # Sample document
    document = """
    Artificial Intelligence (AI) is transforming industries worldwide. Companies like Google, 
    Microsoft, and OpenAI are leading the charge. The global AI market is expected to reach 
    $1.5 trillion by 2030.
    
    Key benefits include: improved efficiency, cost reduction, and enhanced decision-making. 
    However, challenges remain. Ethical concerns, job displacement, and data privacy are 
    significant issues that need addressing.
    
    Dr. Jane Smith, CEO of TechCorp, states: "AI isn't just the future; it's the present. 
    Organizations that don't adapt will be left behind." Industry experts agree that 2024 
    will be a pivotal year for AI adoption.
    """
    
    # Extract and normalize sentences
    sentence_normalizer = SentenceNormalizer(
        min_length=30,
        strip_sentences=True
    )
    
    sentences = await sentence_normalizer.transform(document)
    print(f"Extracted {len(sentences)} significant sentences:")
    for i, sentence in enumerate(sentences[:3], 1):
        print(f"  {i}. {sentence}")
    
    # Tokenize and normalize
    # First, let's get words from the normalized text
    text_normalizer = TextNormalizer(
        lowercase=True,
        remove_punctuation=True,
        remove_numbers=False  # Keep numbers for analysis
    )
    
    normalized = await text_normalizer.transform(document)
    tokens = normalized.split()
    
    # Filter tokens
    token_normalizer = TokenNormalizer(
        min_length=4,
        lowercase=True,
        remove_numbers=True
    )
    
    filtered_tokens = await token_normalizer.transform(tokens)
    
    # Get word frequency
    from collections import Counter
    word_freq = Counter(filtered_tokens)
    
    print(f"\nToken analysis:")
    print(f"  Total tokens: {len(tokens)}")
    print(f"  Filtered tokens: {len(filtered_tokens)}")
    print(f"  Unique words: {len(set(filtered_tokens))}")
    
    print("\nMost common words:")
    for word, count in word_freq.most_common(10):
        print(f"  - {word}: {count}")


async def demo_dataframe_operations():
    """Demonstrate DataFrame operations (requires pandas)."""
    print("\n=== DataFrame Operations Demo ===\n")
    
    try:
        import pandas as pd
    except ImportError:
        print("⚠️  pandas not installed. Install with: pip install pandas")
        print("   Skipping DataFrame demo.")
        return
    
    # Sample sales data
    sales_data = [
        {"date": "2024-01-01", "product": "Laptop", "category": "Electronics", "price": 999.99, "quantity": 5, "region": "North"},
        {"date": "2024-01-01", "product": "Mouse", "category": "Electronics", "price": 29.99, "quantity": 15, "region": "North"},
        {"date": "2024-01-02", "product": "Laptop", "category": "Electronics", "price": 999.99, "quantity": 3, "region": "South"},
        {"date": "2024-01-02", "product": "Chair", "category": "Furniture", "price": 199.99, "quantity": 8, "region": "South"},
        {"date": "2024-01-03", "product": "Desk", "category": "Furniture", "price": 449.99, "quantity": 4, "region": "North"},
        {"date": "2024-01-03", "product": "Mouse", "category": "Electronics", "price": 29.99, "quantity": 20, "region": "South"},
        {"date": "2024-01-04", "product": "Chair", "category": "Furniture", "price": 199.99, "quantity": 10, "region": "North"},
        {"date": "2024-01-04", "product": "Laptop", "category": "Electronics", "price": 999.99, "quantity": 2, "region": "North"},
    ]
    
    # 1. Filter high-value sales
    print("1. Filtering high-value sales (>$500):")
    
    # Add total column
    for item in sales_data:
        item["total"] = item["price"] * item["quantity"]
    
    filter_op = DataFrameFilter(
        column="total",
        value=500,
        op=">"
    )
    
    high_value_sales = await filter_op.transform(sales_data)
    print(f"   Found {len(high_value_sales)} high-value transactions")
    print(f"   Sample: {high_value_sales.iloc[0]['product']} - ${high_value_sales.iloc[0]['total']:,.2f}")
    
    # 2. Group by category and aggregate
    print("\n2. Sales by category:")
    
    groupby_op = DataFrameGroupBy(
        by="category",
        agg={
            "quantity": "sum",
            "total": ["sum", "mean", "count"]
        }
    )
    
    category_summary = await groupby_op.transform(sales_data)
    print(category_summary.to_string())
    
    # 3. Pivot table - sales by region and category
    print("\n3. Pivot table - sales by region and category:")
    
    pivot_op = DataFrameReshape(
        reshape_type="pivot",
        index="region",
        columns="category",
        values="total",
        aggfunc="sum"
    )
    
    pivot_result = await pivot_op.transform(sales_data)
    print(pivot_result.to_string())
    
    # 4. Time-based analysis
    print("\n4. Daily sales trend:")
    
    # Group by date
    date_groupby = DataFrameGroupBy(
        by="date",
        agg={"total": "sum", "quantity": "sum"}
    )
    
    daily_sales = await date_groupby.transform(sales_data)
    print(daily_sales.to_string())
    
    # 5. Merge with product info
    print("\n5. Merging with product information:")
    
    product_info = pd.DataFrame([
        {"product": "Laptop", "supplier": "TechCorp", "cost": 700.00},
        {"product": "Mouse", "supplier": "TechCorp", "cost": 15.00},
        {"product": "Chair", "supplier": "FurniturePlus", "cost": 100.00},
        {"product": "Desk", "supplier": "FurniturePlus", "cost": 250.00},
    ])
    
    merge_op = DataFrameMerge(
        other=product_info,
        how="left",
        on="product"
    )
    
    enriched_data = await merge_op.transform(sales_data)
    
    # Calculate profit
    enriched_data["profit"] = (enriched_data["price"] - enriched_data["cost"]) * enriched_data["quantity"]
    
    # Group by supplier
    supplier_groupby = DataFrameGroupBy(
        by="supplier",
        agg={"profit": "sum", "quantity": "sum"}
    )
    
    supplier_summary = await supplier_groupby.transform(enriched_data)
    print("\nProfit by supplier:")
    print(supplier_summary.to_string())
    
    # 6. Complex filtering with query
    print("\n6. Complex filtering - Electronics in North region with quantity > 5:")
    
    complex_filter = DataFrameFilter(
        query="category == 'Electronics' and region == 'North' and quantity > 5"
    )
    
    filtered_result = await complex_filter.transform(sales_data)
    print(f"   Found {len(filtered_result)} matching records")
    for _, row in filtered_result.iterrows():
        print(f"   - {row['date']}: {row['product']} x{row['quantity']}")


async def main():
    """Run all transformer demos."""
    print("\n🚀 Advanced Transformers in Nanobricks\n")
    
    await demo_csv_processing()
    await demo_text_normalization()
    await demo_smart_type_conversion()
    await demo_data_pipeline()
    await demo_advanced_text_processing()
    await demo_dataframe_operations()
    
    print("\n✅ All transformer demos complete!\n")


if __name__ == "__main__":
    asyncio.run(main())