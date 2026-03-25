from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.system.vector_db.adapters.abs_database import AbstractDataBase
from src.system.vector_db.domain.domain import DocumentCreate, DocumentResponse, DocumentSearch, SearchResult

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = AbstractDataBase()


@app.post("/documents", response_model=DocumentResponse)
def create_document(doc: DocumentCreate):
    doc_id = db.insert_embedding(doc.embedding, doc.metadata)
    result = db.get_by_id(doc_id)
    return DocumentResponse(**result)


# @app.get("/documents/{doc_id}", response_model=DocumentResponse)
# def get_document(doc_id: int):
#     result = db.get_by_id(doc_id)
#     if not result:
#         raise HTTPException(status_code=404, detail="Document not found")
#     return DocumentResponse(**result)


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int):
    deleted = db.delete_by_id(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}


@app.post("/search", response_model=list[SearchResult])
def search_documents(search: DocumentSearch):
    results = db.search_similar(search.embedding, search.limit)
    return [SearchResult(**result) for result in results]


@app.post("/setup")
def setup_database(recreate: bool = False):
    db.setup_vector_db(recreate=recreate)
    return {"message": "Database setup complete"}
