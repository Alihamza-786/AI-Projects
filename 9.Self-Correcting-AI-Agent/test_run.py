"""Quick test without Chainlit: run one task and print what each agent did."""

import asyncio

from langgraph_app import my_graph
from utils import TEST_FILE, read_file, reset_sandbox

TASK = "Write Python code to calculate the average of a list."


async def main():
    reset_sandbox()
    result = await my_graph.ainvoke({"messages": [{"role": "user", "content": TASK}]})

    # Show the conversation between the main agent and its team
    for msg in result["messages"]:
        if msg.type == "ai" and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"\n>>> MAIN calls {tc['name']}:\n{tc['args']}")
        elif msg.type == "tool":
            print(f"\n<<< {msg.name} replied:\n{msg.content}")

    print("\n========== FINAL ANSWER ==========\n")
    print(result["messages"][-1].content)

    print("\n========== TESTS THE TESTER WROTE ==========\n")
    print(read_file(TEST_FILE))


asyncio.run(main())
