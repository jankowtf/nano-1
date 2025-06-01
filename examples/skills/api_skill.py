# Import skills to trigger registration
from nanobricks import NanobrickSimple, skill


@skill("api", path="/analyze", port=8000, docs=True)
class TextAnalyzerBrick(NanobrickSimple[str, dict]):
    """Analyzes text and returns statistics."""

    async def invoke(self, input: str, *, deps=None) -> dict:
        words = input.split()
        return {
            "text": input,
            "word_count": len(words),
            "unique_words": len(set(words)),
        }


if __name__ == "__main__":
    analyzer = TextAnalyzerBrick()

    # Show example usage
    import asyncio

    result = asyncio.run(analyzer.invoke("Hello world from API example!"))
    print(f"Direct invocation result: {result}")
    print("\n" + "=" * 60)
    print("🚀 Starting API server...")
    print("=" * 60)
    print("\n📍 API Endpoints:")
    print("  - GET  http://localhost:8080/       (Web Interface)")
    print("  - POST http://localhost:8080/analyze (API Endpoint)")
    print("  - GET  http://localhost:8080/health  (Health Check)")
    print("  - GET  http://localhost:8080/docs    (Swagger UI)")
    print("\n💡 Quick test:")
    print("  curl -X POST http://localhost:8080/analyze \\")
    print("    -H 'Content-Type: application/json' \\")
    print('    -d \'{"data": "Hello API!"}\'')
    print("\n🌐 Open http://localhost:8080/ in your browser for the web interface!")
    print("   Or visit http://localhost:8080/docs for API documentation")
    print("\nPress Ctrl+C to stop the server...\n")

    try:
        analyzer.start_server()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped gracefully!")
