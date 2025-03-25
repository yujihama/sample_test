from src.core.workflow import clean_workflow
import asyncio

async def main():
    workflow_id = "67615edc-03ed-4a9b-b109-11cb0b3a3432"
    print(f"Cleaning workflow: {workflow_id}")
    result = await clean_workflow(workflow_id)
    print(f"Cleanup result: {result}")

if __name__ == "__main__":
    asyncio.run(main()) 