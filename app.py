import os
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from chromadb import PersistentClient

from project_contract import ProjectContract

PERSISTENT_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "your_collection_name"
DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"

console = Console()

_project = None
_client = None
_collection = None
_model = None

# -------------------------------
# 1) Set Up ChromaDB
# -------------------------------

def load_project(path: str | None = None) -> ProjectContract:
    global _project

    if path is not None:
        return ProjectContract.from_file(path)

    if _project is None:
        _project = ProjectContract.from_file()

    return _project


def knowledge_directory() -> str:
    return str(load_project().knowledge_path())


def create_collection(persist_directory: str = PERSISTENT_DIRECTORY, collection_name: str = COLLECTION_NAME):

    client = PersistentClient(path=persist_directory)
    return client, client.get_or_create_collection(collection_name)


def get_collection():
    global _client, _collection

    if _collection is None:
        _client, _collection = create_collection(PERSISTENT_DIRECTORY, COLLECTION_NAME)

    return _collection

# -------------------------------
# 2) Set Up Sentence Transformers
# -------------------------------

def create_embedding_model(model_name: str = DEFAULT_MODEL_NAME):
    return SentenceTransformer(model_name)


def get_model():
    global _model

    if _model is None:
        _model = create_embedding_model()

    return _model

def get_embedding(text: str) -> list:
    """
    Generate an embedding for the given text using Sentence Transformers.
    """
    try:
        embedding = get_model().encode(text)
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        return embedding
    except Exception as e:
        console.print(f"[red]Error obtaining embedding: {e}[/red]")
        return None

# -------------------------------
# 3) Utility: Track Processed Files
# -------------------------------
PROCESSED_FILES_NAME = "processed_files.json"


def processed_files_path() -> Path:
    return Path(load_project().root) / PROCESSED_FILES_NAME

def load_processed_files():
    """
    Returns a dict with { file_id: { modified: str, vectors: [vector_ids], name: str }, ...}
    """
    path = processed_files_path()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_processed_files(processed):
    path = processed_files_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2)

# -------------------------------
# 4) Get Local Files
# -------------------------------

def read_local_file(file_path: str) -> str:
    """
    Read a file from the local 'documents' directory and return its content as a string.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        console.print(f"[red]Error reading file {file_path}: {e}[/red]")
        return ""

# -------------------------------
# 5) Split Text into Chunks
# -------------------------------
def split_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """
    Split large text into smaller chunks for embedding.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks

# -------------------------------
# 6) Process a Single File
# -------------------------------

def process_file(file_path: str):
    file_name = os.path.basename(file_path)
    console.rule(f"[bold blue]Processing File: {file_name}")

    # 1. Read the file
    content = read_local_file(file_path)
    if not content:
        console.print(f"[red]No content for file {file_name}[/red]")
        return

    # 2. Split into chunks
    chunks = split_text(content)
    console.print(f"[green]Split text into {len(chunks)} chunks.[/green]")

    # 3. Embed and Upsert
    vector_ids = []
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        if embedding is None:
            continue

        vector_id = f"{file_name}_{i}"
        vector_ids.append(vector_id)

        metadata = {
            "file_name": file_name,
            "chunk_index": i,
            "text": chunk[:200]  # Store a preview
        }

        try:
            # print(embedding)
            get_collection().add(
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[chunk],
                ids=[vector_id]
            )
            console.print(f"[green]Upserted chunk {i} successfully.[/green]")
        except Exception as e:
            console.print(f"[red]Error upserting vector: {e}[/red]")

    # 4. Save processed state
    processed = load_processed_files()
    processed[file_name] = {
        "modified": os.path.getmtime(file_path),
        "vectors": vector_ids,
        "name": file_name
    }
    save_processed_files(processed)

    console.print("[bold green]File processed & upserted to ChromaDB.[/bold green]\n")

# -------------------------------
# 7) Delete Vectors for a File
# -------------------------------

def delete_vectors(file_name: str):
    """
    Remove existing vectors for a file using metadata filter in ChromaDB.
    """
    processed = load_processed_files()
    try:
        get_collection().delete(where={"file_name": file_name})
        console.print(f"Used metadata filter to delete vectors for {file_name}")
        return True
    except Exception as e:
        console.print(f"[red]Metadata filter deletion failed: {e}[/red]")
        return False

# -------------------------------
# 8) Poll & Update:
#     Checks for new/changed/deleted files in your Drive folder.
# -------------------------------
def list_local_files():
    """
    List all text files in the 'documents' folder.
    """
    folder_path = knowledge_directory()
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    files = []
    for root, dirs, filenames in os.walk(folder_path):
        for filename in filenames:
            if filename.endswith('.md'):
                    file_path = os.path.join(root, filename)
                    files.append({
                    "path": file_path,
                    "name": os.path.relpath(file_path, folder_path),
                    "modified": os.path.getmtime(file_path)
                })

    return files
def upsert_project_profile() -> None:
    project = load_project()
    profile = {
        "project_name": project.name,
        "project_root": project.root,
        "knowledge_dir": project.knowledge_dir,
        "reports_dir": project.reports_dir,
        "architecture": project.architecture,
    }

    content = json.dumps(profile, indent=2, ensure_ascii=False)
    embedding = get_embedding(content)

    if embedding is None:
        return

    get_collection().upsert(
        ids=[f"project:{project.name}"],
        embeddings=[embedding],
        documents=[content],
        metadatas=[{
            "type": "project_profile",
            "project_name": project.name,
            "has_architecture": bool(project.architecture),
        }],
    )

def update_files():
    console.print(f"\n=== Update started {datetime.now().isoformat()} ===\n")
    processed = load_processed_files()
    upsert_project_profile()

    try:
        current_files = list_local_files()

        # 1) Handle deletions
        for file_name in list(processed.keys()):
            file_path = os.path.join(knowledge_directory(), file_name)
            if not os.path.exists(file_path):
                console.print(f"Removing vectors for deleted file: {file_name}")
                if delete_vectors(file_name):  # <=== This now properly deletes old entries
                    del processed[file_name]
                    save_processed_files(processed)

        # 2) Handle new or modified files
        for file in current_files:
            existing = processed.get(file["name"])
            if (not existing) or (file["modified"] > existing["modified"]):
                console.print(f"Deleting old vectors for: {file['name']}")  # Debugging
                delete_vectors(file["name"])  # <=== ADD THIS before reprocessing!
                process_file(file["path"])  # Reprocess file after deleting old entries

    except Exception as e:
        console.print(f"Update failed: {str(e)}")

# -------------------------------
# Optional: A simple main loop
# -------------------------------
def wait_or_pull(interval=3600):
    """
    Wait for a specified interval, but allow typing 'pull' to do an immediate update
    or 'q' to quit.
    """
    start_time = time.time()
    while time.time() - start_time < interval:
        user_input = input("Type 'pull' to run update immediately or 'q' to quit: ").strip().lower()
        if user_input == "pull":
            return
        elif user_input == "q":
            print("Exiting...")
            sys.exit(0)
        time.sleep(1)

if __name__ == "__main__":
    while True:
        update_files()
        wait_or_pull()
