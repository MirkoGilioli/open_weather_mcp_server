import asyncio
import json

from fastmcp import Client

async def test_server():
    # Test the MCP server using streamable-http transport.
    # Use "/sse" endpoint if using sse transport.
    async with Client("http://localhost:8080/mcp") as client:
        # List available tools
        tools = await client.list_tools()
        for tool in tools:
            print(f">>> Tool found: {tool.name}")
        # Call get_weather tool
        print(">>>  Calling get weather tool for London")
        result = await client.call_tool("get_weather", {"city": "London"})
        # The result data is now a dictionary
        print(f"<<<  Result (raw): {result.data}")
        if isinstance(result.data, dict) and "error" not in result.data:
            # Pretty-print the JSON for readability
            print("<<< Result (formatted):")
            print(json.dumps(result.data, indent=2))
            try:
                temp = result.data.get("main", {}).get("temp")
                desc = result.data.get("weather", [{}])[0].get("description")
                print(f"Weather in London: {temp}°C, {desc}")
            except (IndexError, AttributeError):
                print("Could not parse weather data from response.")
        else:
            print(f"Received an error or unexpected data: {result.data}")
        
        # Call get_air_pollution tool
        print("\n>>>  Calling get air pollution tool for London")
        result = await client.call_tool("get_air_pollution", {"city": "London"})
        print(f"<<<  Result (raw): {result.data}")
        if isinstance(result.data, dict) and "error" not in result.data:
            print("<<< Result (formatted):")
            print(json.dumps(result.data, indent=2))
            try:
                aqi = result.data.get("list", [{}])[0].get("main", {}).get("aqi")
                print(f"Air Quality Index (AQI) in London: {aqi}")
            except (IndexError, AttributeError):
                print("Could not parse AQI from response.")
        else:
            print(f"Received an error or unexpected data: {result.data}")
        
        #List all available MCP Resources

        # Get the london weather resource
        print("\n>>> Getting resource 'mcp://weather/london.json'")
        resource_data = await client.read_resource(uri="mcp://weather/london.json")
        print(f"<<< Resource data (raw text): {resource_data[0].text}")
        # The server returns a dict, which is serialized to a string in the Resource.text field
        weather_json = json.loads(resource_data[0].text)
        print("<<< Resource data (formatted JSON):")
        print(json.dumps(weather_json, indent=2))



if __name__ == "__main__":
    asyncio.run(test_server())
