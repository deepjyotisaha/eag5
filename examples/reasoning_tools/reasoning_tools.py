from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import math

mcp = FastMCP("ReasoningDemo")

@mcp.tool()
def show_reasoning_steps(steps: list) -> list[str]:
    """Display step-by-step reasoning process"""
    print(f"CALLED: show_reasoning_steps({steps})")
    return steps

@mcp.tool()
def evaluate_math(expression: str) -> float:
    """Safely evaluate a mathematical expression"""
    print(f"CALLED: evaluate_math({expression})")
    try:
        # In production, use a safer evaluation method
        result = float(eval(expression))
        return result
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def verify_solution(original: str, solution: float) -> bool:
    """Verify if a solution is correct"""
    print(f"CALLED: verify_solution({original}, {solution})")
    try:
        expected = float(eval(original))
        return abs(expected - solution) < 1e-10
    except:
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio") 