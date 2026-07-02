from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from nodes.artifact_generator import artifact_generator
from nodes.discovery import discovery
from nodes.plan import plan
from nodes.developer import developer


def route_after_plan(state: AgentState) -> str:
    if state["plan_approved"]:
        return "developer"
    return END


def build_graph():
    graph = StateGraph(AgentState)

    # nodes
    graph.add_node("artifact_generator", artifact_generator)
    graph.add_node("discovery", discovery)
    graph.add_node("plan", plan)
    graph.add_node("developer", developer)

    # edges
    graph.set_entry_point("artifact_generator")
    graph.add_edge("artifact_generator", "discovery")
    graph.add_edge("discovery", "plan")
    graph.add_conditional_edges("plan", route_after_plan, {
        "developer": "developer",
        END: END
    })
    graph.add_edge("developer", END)

    # compile with memory checkpointer for resumability
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


app = build_graph()