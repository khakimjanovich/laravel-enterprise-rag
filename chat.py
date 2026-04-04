import sys
from ollama import chat
from rich.console import Console

from memory_review import add_review_item, list_open_items, resolve_item

try:
    from app import get_collection, get_embedding, console
except ImportError:
    print("Make sure 'app.py' is in the same folder and named appropriately.")
    sys.exit(1)


def main():
    """
    Run the company documents chat interface.
    """
    console.rule("[bold magenta]Company Documents Chat[/]")
    console.print("[bold green]Type 'exit' to quit.[/]\n")

    while True:
        query = console.input("[bold cyan]Your Question> [/]").strip()
        if query.lower() in ("exit", "quit"):
            break

        if query == "/review":
            items = list_open_items()
            if not items:
                console.print("[green]No open gaps or inconsistencies.[/green]")
                continue

            for item in items:
                console.print(
                    f"[yellow]#{item['id']}[/yellow] [{item['kind']}] {item['title']}\n"
                    f"{item['details']}\n"
                    f"source: {item['source']}\n"
                )
            continue

        if query.startswith("/accept-memory "):
            item_id = int(query.split()[-1])
            ok = resolve_item(item_id, "update_memory")
            console.print("[green]Updated.[/green]" if ok else "[red]Not found.[/red]")
            continue

        if query.startswith("/fix "):
            item_id = int(query.split()[-1])
            ok = resolve_item(item_id, "fix_inconsistency")
            console.print("[green]Marked for fix.[/green]" if ok else "[red]Not found.[/red]")
            continue

        answer = chat_agent(query)
        console.print(f"\n[bold yellow]Answer:[/] {answer}\n")


def chat_agent(query: str) -> str:
    """
    1) Embed the query
    2) Retrieve top matches from ChromaDB
    3) Pass them into the Ollama Chat model for a final answer
    """
    system_message = (
        "You are a helpful HR assistant designed to answer employee questions based on company policies. "
        "Retrieve relevant information from the provided internal documents and provide a concise, accurate answer. "
        "If the answer cannot be found in the provided documents, say 'I cannot find the answer in the available resources.'"
    )

    # 1) Embed the user query
    query_embedding = get_embedding(query)
    if query_embedding is None:
        return "Error obtaining query embedding."

    # 2) Query ChromaDB
    try:
        results = get_collection().query(
            query_embeddings=[query_embedding],
            n_results=3
        )
    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"

    if not results or "documents" not in results or not results["documents"]:
        return "I cannot find the answer in the available resources."

    # Combine top results into a single string for context
    documents = results["documents"][0]
    context = " ".join(documents)
    if not context.strip():
        return "I cannot find the answer in the available resources."

    review_hint = (
        "If you detect a missing rule, answer with prefix 'GAP:'. "
        "If you detect conflicting knowledge, answer with prefix 'INCONSISTENCY:'. "
        "Otherwise answer normally."
    )

    response = ollama_chat(system_message + "\n" + review_hint, query, context)

    if response.startswith("GAP:"):
        add_review_item(
            kind="gap",
            title=query,
            details=response[4:].strip(),
            source="chat",
        )

    if response.startswith("INCONSISTENCY:"):
        add_review_item(
            kind="inconsistency",
            title=query,
            details=response[len("INCONSISTENCY:"):].strip(),
            source="chat",
        )

    return response


def ollama_chat(system_message: str, query: str, context: str) -> str:
    """
    Calls Ollama's chat completion with a system message, user's query, and retrieved context.
    """
    try:
        response = chat(
            model='deepseek-coder-v2:16b',
            messages=[
                {
                    'role': 'system',
                    'content': f"{system_message}\n\nContext: {context}"
                },
                {
                    'role': 'user',
                    'content': query
                }
            ],
            stream=False  # Set to True if you want to handle streaming responses
        )
        return response['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    main()
