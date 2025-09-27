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
        
        # List and read all available MCP Resources
        print("\n>>> Listing and reading all available resources")
        resources = await client.list_resources()
        for resource in resources:
            print(f"\n>>> Getting resource '{resource.uri}'")
            resource_data = await client.read_resource(uri=resource.uri)
            content = resource_data[0].text
            print(f"<<< Resource data (raw text): {content}")

            # Try to parse as JSON for pretty printing
            try:
                data_json = json.loads(content)
                print("<<< Resource data (formatted JSON):")
                print(json.dumps(data_json, indent=2))
            except json.JSONDecodeError:
                # Not a JSON, just print the raw text
                print("<<< Resource data is not JSON.")



if __name__ == "__main__":
    asyncio.run(test_server())
