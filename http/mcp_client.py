import asyncio

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
        print(f"<<<  Result: {result.data}")

if __name__ == "__main__":
    asyncio.run(test_server())
