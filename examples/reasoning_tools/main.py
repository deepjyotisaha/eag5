import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import google.generativeai as genai
import asyncio
from concurrent.futures import TimeoutError
from datetime import datetime
import logging
import sys

# Configure logging at the start of your file, after the imports
logging.basicConfig(
    #filename='mcp_client.log',
    #filemode='a',  # append mode
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)20s() %(message)s',
    handlers=[
        logging.FileHandler('reasoning_tools_client.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)


# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

logging.info("Configuring Gemini API...")
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    logging.info("Gemini API configured successfully")
except Exception as e:
    logging.error(f"Error configuring Gemini API: {str(e)}")
    raise

async def generate_with_timeout(prompt, timeout=10):
    """Generate content with a timeout"""
    logging.info("Starting LLM generation...")
    try:
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: model.generate_content(
                    contents=prompt
                )
            ),
            timeout=timeout
        )
        logging.info("LLM generation completed")
        return response
    except TimeoutError:
        logging.error("LLM generation timed out!")
        raise
    except Exception as e:
        logging.error(f"Error in LLM generation: {e}")
        raise

async def main():
    try:
        # Connect to MCP server
        server_params = StdioServerParameters(
            command="python",
            args=["reasoning_tools.py"]
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Get available tools
                tools_result = await session.list_tools()
                tools = tools_result.tools

                # Create system prompt with available tools
                system_prompt = create_system_prompt(tools)
                
                # Example reasoning problems
                problems = [
                    "Solve step by step: If I have 5 apples and give away 2, then get 3 more, how many do I have?",
                    "Calculate (17 + 8) × 3 showing all steps",
                    "Find the sum of numbers from 1 to 5 showing your work"
                ]

                for problem in problems:
                    logging.info(f"\nSolving problem: {problem}")
                    await solve_problem(session, system_prompt, problem)

    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()

def create_system_prompt(tools):
    # Create tools description
    tools_description = []
    for tool in tools:
        params = tool.inputSchema
        desc = getattr(tool, 'description', 'No description available')
        name = getattr(tool, 'name', 'unknown_tool')
        
        if 'properties' in params:
            param_details = [f"{p}: {info.get('type', 'unknown')}" 
                           for p, info in params['properties'].items()]
            params_str = ', '.join(param_details)
        else:
            params_str = 'no parameters'

        tools_description.append(f"{name}({params_str}) - {desc}")

    return f"""You are a mathematical reasoning agent that demonstrates logical thinking.

Available tools:
{chr(10).join(tools_description)}

You must respond with EXACTLY ONE line in one of these formats:
1. For function calls:
   FUNCTION_CALL: function_name|param1|param2|...
   
2. For final answers:
   FINAL_ANSWER: [your answer]

Important:
- Break down complex problems into steps
- Show your reasoning process
- Verify your answers
- Only give FINAL_ANSWER when you have completed all calculations

DO NOT include any explanations or additional text."""

async def solve_problem(session, system_prompt, problem):
    prompt = f"{system_prompt}\n\nProblem: {problem}"
    logging.info("\n\nPrompt: %s", prompt)
    response = await generate_with_timeout(prompt)
    
    if response and response.text:
        result = response.text.strip()
        logging.info(f"Model response: {result}")
        
        if result.startswith("FUNCTION_CALL:"):
            # Handle function call
            _, function_info = result.split(":", 1)
            parts = [p.strip() for p in function_info.split("|")]
            func_name, params = parts[0], parts[1:]
            
            # Call the appropriate tool
            result = await session.call_tool(func_name, arguments={"steps": params})
            logging.info(f"Tool result: {result}")

if __name__ == "__main__":
    asyncio.run(main())