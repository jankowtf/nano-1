import asyncio

# Import skills to trigger registration
from nanobricks import NanobrickSimple, skill


@skill("logging", log_inputs=True, log_outputs=True, log_errors=True)
class TemperatureConverterBrick(NanobrickSimple[float, dict]):
    """Converts temperature between Celsius, Fahrenheit, and Kelvin."""

    async def invoke(self, input: float, *, deps=None) -> dict:
        # Simulate some processing time
        await asyncio.sleep(0.1)

        # Sometimes fail for demonstration
        if input < -273.15:
            raise ValueError(f"Temperature {input}°C is below absolute zero!")

        # Convert from Celsius to other units
        fahrenheit = (input * 9 / 5) + 32
        kelvin = input + 273.15

        return {
            "celsius": round(input, 2),
            "fahrenheit": round(fahrenheit, 2),
            "kelvin": round(kelvin, 2),
            "description": self._get_description(input),
        }

    def _get_description(self, celsius: float) -> str:
        """Get a human-readable description of the temperature."""
        if celsius < -20:
            return "🥶 Extremely cold"
        elif celsius < 0:
            return "❄️ Freezing"
        elif celsius < 10:
            return "🧊 Cold"
        elif celsius < 20:
            return "🌤️ Cool"
        elif celsius < 30:
            return "☀️ Warm"
        elif celsius < 40:
            return "🔥 Hot"
        else:
            return "🌋 Extremely hot"


@skill("logging", log_inputs=True, log_outputs=True, truncate_at=50)
class WeatherAnalyzerBrick(NanobrickSimple[dict, str]):
    """Analyzes weather data and provides recommendations."""

    async def invoke(self, input: dict, *, deps=None) -> str:
        temp = input.get("temperature", 20)
        humidity = input.get("humidity", 50)
        wind_speed = input.get("wind_speed", 10)

        # Create a detailed analysis
        analysis = "Weather Analysis:\n"
        analysis += f"Temperature: {temp}°C\n"
        analysis += f"Humidity: {humidity}%\n"
        analysis += f"Wind Speed: {wind_speed} km/h\n\n"

        # Add recommendations
        if temp < 10:
            analysis += "❄️ Recommendation: Wear warm clothing!\n"
        elif temp > 30:
            analysis += "☀️ Recommendation: Stay hydrated and seek shade!\n"

        if humidity > 80:
            analysis += (
                "💧 High humidity - it may feel warmer than actual temperature.\n"
            )

        if wind_speed > 30:
            analysis += "💨 Strong winds - secure loose objects!\n"

        return analysis


if __name__ == "__main__":
    print("🔍 Logging Skill Demo")
    print("=" * 60)
    print("\nThe logging skill automatically logs:")
    print("  ✓ Input values")
    print("  ✓ Output values")
    print("  ✓ Errors and exceptions")
    print("  ✓ Execution time")
    print("\n" + "=" * 60 + "\n")

    # Demo 1: Temperature Converter
    print("📊 Demo 1: Temperature Converter (with automatic logging)")
    print("-" * 40)

    converter = TemperatureConverterBrick()

    # Test with various temperatures
    test_temps = [0, 25, 100, -40, -300]  # Last one will cause error

    for temp in test_temps:
        try:
            result = asyncio.run(converter.invoke(temp))
            print(f"✅ {temp}°C converted successfully")
        except ValueError as e:
            print(f"❌ Error for {temp}°C: {e}")
        print()  # Space between logs

    print("\n" + "=" * 60 + "\n")

    # Demo 2: Weather Analyzer with truncation
    print("📊 Demo 2: Weather Analyzer (with output truncation)")
    print("-" * 40)

    analyzer = WeatherAnalyzerBrick()

    weather_data = [
        {"temperature": 25, "humidity": 60, "wind_speed": 15},
        {"temperature": -5, "humidity": 40, "wind_speed": 35},
        {"temperature": 35, "humidity": 85, "wind_speed": 5},
    ]

    for data in weather_data:
        result = asyncio.run(analyzer.invoke(data))
        print(f"✅ Analysis complete for {data['temperature']}°C")
        print()

    print("\n" + "=" * 60)
    print("\n💡 Check the logs above to see automatic logging in action!")
    print("   - Input/output values are logged automatically")
    print("   - Errors are captured and logged")
    print("   - Long outputs are truncated (see WeatherAnalyzer)")
    print("\n📝 Note: In production, logs would go to your configured logger")
