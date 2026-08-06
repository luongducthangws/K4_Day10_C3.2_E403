from pathlib import Path
import sys

# Ensure src/ is in sys.path
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question
from retrieval.agent import build_agent, run_agent_question


def main() -> None:
    print("=====================================================")
    print("  SCHOLARLY PAPER RAG AGENT & OBSERVABILITY DEMO CLI ")
    print("=====================================================")

    settings = load_settings()
    if not settings.paths.embeddings_json.exists():
        print("Error: Embedding index not found. Please run 'python script/run_phase1.py' first.")
        sys.exit(1)

    print(f"Loading Chroma vector index from {settings.paths.embeddings_json}...")
    index = LocalEmbeddingIndex.load(settings)
    print(f"Index loaded successfully! (Collection: '{index.collection_name}', Total docs: {len(index.documents)})")
    print(f"Active LLM Provider: {settings.llm_provider} (Model: {settings.model_name})")
    print("-" * 55)

    try:
        agent = build_agent(settings, index)
        has_agent = True
    except Exception as e:
        print(f"Notice: Agent initialization fallback mode ({e}). Utilizing retrieval QA engine.")
        has_agent = False

    while True:
        try:
            print("\nEnter your question (or 'exit' / 'report'):")
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "q"}:
                print("Goodbye!")
                break
            if user_input.lower() in {"report", "status"}:
                if settings.paths.baseline_report.exists():
                    print("\n--- PHASE 1 BASELINE REPORT SUMMARY ---")
                    print(settings.paths.baseline_report.read_text(encoding="utf-8")[:1000])
                    print("...\n--------------------------------------")
                else:
                    print("Report not generated yet.")
                continue

            print("\nSearching paper corpus...")
            if has_agent:
                try:
                    answer = run_agent_question(agent, user_input)
                    print(f"\n[Agent Answer]:\n{answer}")
                except Exception as exc:
                    print(f"Agent error ({exc}), using retrieval QA fallback:")
                    res = answer_question(user_input, settings, index)
                    print(f"\n[Retrieval QA Answer]: {res.answer}")
                    print(f"Retrieved Doc IDs: {res.retrieved_doc_ids}")
            else:
                res = answer_question(user_input, settings, index)
                print(f"\n[Retrieval QA Answer]: {res.answer}")
                print(f"Retrieved Doc IDs: {res.retrieved_doc_ids}")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting CLI.")
            break


if __name__ == "__main__":
    main()
