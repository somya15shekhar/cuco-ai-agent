from langgraph.graph import StateGraph, END
from typing import Dict, Any

from app.agent.state import AgentState
from app.models.claim import ParsedClaim
from app.agent.nodes import (
    intake_node,
    eligibility_node,
    preauth_node,
    fetch_primary_plan_node,
    fetch_secondary_plan_node,
    cob_node,
    validation_node,
    reflection_node,
    output_node
)

# 1. Initialize StateGraph
workflow = StateGraph(AgentState)

# 2. Add Nodes
workflow.add_node("intake", intake_node)
workflow.add_node("eligibility", eligibility_node)
workflow.add_node("preauth", preauth_node)
workflow.add_node("fetch_primary", fetch_primary_plan_node)
workflow.add_node("fetch_secondary", fetch_secondary_plan_node)
workflow.add_node("cob", cob_node)
workflow.add_node("validation", validation_node)
workflow.add_node("reflection", reflection_node)
workflow.add_node("output", output_node)

# 3. Set Entry Point
workflow.set_entry_point("intake")

# 4. Define Transitions & Routing Logic

def route_eligibility(state: AgentState) -> str:
    """Routes to preauth if eligible, else skips directly to output node."""
    status = state.get("eligibility_status")
    if status and not status.get("is_eligible", False):
        return "output"
    return "preauth"

def route_validation(state: AgentState) -> str:
    """Routes to reflection node if there are errors and retry count < 3, else outputs results."""
    errors = state.get("validation_errors", [])
    retry = state.get("retry_count", 0)
    if len(errors) > 0 and retry < 3:
        return "reflection"
    return "output"

# Add standard edges
workflow.add_edge("intake", "eligibility")

# Add conditional eligibility routing
workflow.add_conditional_edges(
    "eligibility",
    route_eligibility,
    {
        "preauth": "preauth",
        "output": "output"
    }
)

workflow.add_edge("preauth", "fetch_primary")
workflow.add_edge("fetch_primary", "fetch_secondary")
workflow.add_edge("fetch_secondary", "cob")
workflow.add_edge("cob", "validation")

# Add conditional validation routing (reflection loop)
workflow.add_conditional_edges(
    "validation",
    route_validation,
    {
        "reflection": "reflection",
        "output": "output"
    }
)

# Reflection loops back to COB recalculation
workflow.add_edge("reflection", "cob")

# End transition
workflow.add_edge("output", END)

# 5. Compile Graph
app_graph = workflow.compile()

def run_cob_agent(parsed_claim: ParsedClaim) -> Dict[str, Any]:
    """Invokes the LangGraph Coordination of Benefits claim processing workflow.
    
    Args:
        parsed_claim: A ParsedClaim input model.
        
    Returns:
        The final structured JSON output dictionary.
    """
    initial_state = {
        "parsed_claim": parsed_claim,
        "primary_plan": None,
        "secondary_plan": None,
        "eligibility_status": None,
        "preauth_status": None,
        "cob_result": None,
        "validation_errors": [],
        "reflection_notes": None,
        "retry_count": 0,
        "final_output": None,
        "execution_log": []
    }
    
    final_state = app_graph.invoke(initial_state)
    return final_state.get("final_output", {})
