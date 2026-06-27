from langgraph.graph import StateGraph, END
from app.agents.langgraph.state import ResearchGraphState
from app.agents.langgraph.nodes import (
    planner_node,
    searcher_node,
    reader_node,
    writer_node,
    critic_node,
    finalizer_node,
)
from app.agents.langgraph.edges import route_after_critique, Route
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_research_graph() -> StateGraph:
    """
    Assembles the research workflow graph.

    Nodes own transformations.
    Edges own transitions.
    Config owns policy values.

    This function is pure assembly — no business logic here.
    """

    graph = StateGraph(ResearchGraphState)

    # ─── Register Nodes ───────────────────────────────────
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_node("reader", reader_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("finalizer", finalizer_node)

    # ─── Entry Point ──────────────────────────────────────
    graph.set_entry_point("planner")

    # ─── Linear Edges ─────────────────────────────────────
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "reader")
    graph.add_edge("reader", "writer")
    graph.add_edge("writer", "critic")

    # ─── Conditional Edge (Transition Policy) ─────────────
    # This is the only branching point in the graph.
    # route_after_critique decides: loop or finalize?
    graph.add_conditional_edges(
        "critic",
        route_after_critique,
        {
            Route.REPLAN: "planner",      # loop back
            Route.WRITE_FINAL: "finalizer",  # exit loop
        }
    )

    # ─── Exit ─────────────────────────────────────────────
    graph.add_edge("finalizer", END)

    logger.info("research graph assembled")

    return graph.compile()


# ─── Singleton Graph Instance ─────────────────────────────
# Compiled once at module load.
# Reused for every research execution.
# Compilation is expensive — never do it per-request.

research_graph = build_research_graph()