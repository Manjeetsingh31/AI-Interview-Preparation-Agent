"""Check ADK 2.3.0 API compatibility."""
from google.adk.agents import Agent
import inspect

print(f"Agent.__init__ sig: {inspect.signature(Agent.__init__)}")

# Try constructing with typical args
try:
    a = Agent(name="test_agent", model="gemini-2.0-flash")
    print("Agent(name=..., model=...) OK")
except Exception as e:
    print(f"Agent(name=..., model=...) FAILED: {type(e).__name__}: {e}")

# Try with data dict
try:
    a = Agent(data={"name": "test_agent"})
    print("Agent(data={{...}}) OK")
except Exception as e:
    print(f"Agent(data={{...}}) FAILED: {type(e).__name__}: {e}")

# Check if Agent is actually a BaseModel
print(f"Agent bases: {Agent.__bases__}")
print(f"Is Pydantic BaseModel: {'BaseModel' in [b.__name__ for b in Agent.__bases__]}")

# Check model_fields
try:
    print(f"Agent model fields: {list(Agent.model_fields.keys())}")
except Exception as e:
    print(f"model_fields error: {e}")
