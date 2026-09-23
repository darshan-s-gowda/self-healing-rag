from typing import TypedDict

from langgraph.graph import StateGraph, END

from .config import MAX_RETRIES, SAFE_FALLBACK
from .llm import chat, parse_json_object
from .prompts import GENERATOR_SYSTEM, CRITIC_SYSTEM, REWRITE_SYSTEM
from .store import retrieve


class State(TypedDict, total=False):
    question: str
    query: str
    evidence: list[dict]
    answer: str

    grounded: bool
    confidence: float

    retries: int
    fallback_count: int

    reformulated_query: str


def retrieve_node(state: State) -> State:
    try:
        evidence = retrieve(state["query"])
    except Exception:
        evidence = []

    return {
        "evidence": evidence
    }


def generate_node(state: State) -> State:
    evidence_text = "\n\n".join(
        f"[Source: {e['source']}, page {e['page']}]\n{e['text']}"
        for e in state.get("evidence", [])
    )

    if not evidence_text:
        return {
            "answer": SAFE_FALLBACK
        }

    user = (
        f"Question: {state['question']}\n\n"
        f"Evidence:\n{evidence_text}"
    )

    try:
        answer = chat(
            GENERATOR_SYSTEM,
            user,
            temperature=0.0
        ).strip()
    except Exception:
        answer = SAFE_FALLBACK

    return {
        "answer": answer or SAFE_FALLBACK
    }


def _critic_fallback() -> dict:
    return {
        "grounded": False,
        "confidence": 0.0,
        "reformulated_query": ""
    }


def critic_node(state: State) -> State:
    answer = state.get("answer", "").strip()

    # The safe fallback is NEVER considered grounded.
    if answer == SAFE_FALLBACK:
        return _critic_fallback()

    evidence_text = "\n\n".join(
        e["text"]
        for e in state.get("evidence", [])
    )

    prompt = (
        f"Question: {state['question']}\n\n"
        f"Proposed answer: {answer}\n\n"
        f"Evidence:\n{evidence_text}"
    )

    try:
        raw = chat(
            CRITIC_SYSTEM,
            prompt,
            temperature=0.0
        )

        data = parse_json_object(raw)

        grounded = bool(data.get("grounded", False))

        verdict = str(
            data.get("verdict", "rejected")
        ).strip().lower()

        # Only an explicit grounded verdict can pass.
        if verdict != "grounded":
            grounded = False

        confidence = max(
            0.0,
            min(
                1.0,
                float(data.get("confidence", 0.0))
            )
        )

        reformulated = str(
            data.get("reformulated_query", "")
        ).strip()

        return {
            "grounded": grounded,
            "confidence": confidence,
            "reformulated_query": reformulated
        }

    except Exception:
        # Fail closed.
        return _critic_fallback()


def route_after_critic(state: State):
    if state.get("grounded", False):
        return "finalize"

    if state.get("retries", 0) >= MAX_RETRIES:
        return "fallback"

    return "rewrite"


def rewrite_node(state: State) -> State:
    retries = state.get("retries", 0) + 1

    suggestion = state.get(
        "reformulated_query",
        ""
    ).strip()

    if suggestion:
        query = suggestion
    else:
        try:
            query = chat(
                REWRITE_SYSTEM,
                state["question"],
                temperature=0.0
            ).strip()
        except Exception:
            query = state["question"]

    return {
        "query": query or state["question"],
        "retries": retries
    }


def finalize_node(state: State) -> State:
    return {
        "answer": state.get(
            "answer",
            SAFE_FALLBACK
        )
    }


def fallback_node(state: State) -> State:
    return {
        "answer": SAFE_FALLBACK,
        "grounded": False,
        "confidence": 0.0,
        "fallback_count": state.get(
            "fallback_count",
            0
        ) + 1
    }


def build_graph():
    graph = StateGraph(State)

    graph.add_node(
        "retrieve",
        retrieve_node
    )

    graph.add_node(
        "generate",
        generate_node
    )

    graph.add_node(
        "critic",
        critic_node
    )

    graph.add_node(
        "rewrite",
        rewrite_node
    )

    graph.add_node(
        "finalize",
        finalize_node
    )

    graph.add_node(
        "fallback",
        fallback_node
    )

    graph.set_entry_point("retrieve")

    graph.add_edge(
        "retrieve",
        "generate"
    )

    graph.add_edge(
        "generate",
        "critic"
    )

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "finalize": "finalize",
            "rewrite": "rewrite",
            "fallback": "fallback"
        }
    )

    graph.add_edge(
        "rewrite",
        "retrieve"
    )

    graph.add_edge(
        "finalize",
        END
    )

    graph.add_edge(
        "fallback",
        END
    )

    return graph.compile()


GRAPH = build_graph()