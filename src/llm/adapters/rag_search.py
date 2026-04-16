from ast import Pass
import os
from langchain_text_splitters import CharacterTextSplitter
from openai import OpenAI
from typing import List
from sentence_transformers import SentenceTransformer

from src.llm.domain.domain import (
    RAGRequest,
    RAGResponse,
)


class RAGSearch:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model_qa = os.getenv("MODEL")

        self.model_embed = SentenceTransformer(os.getenv("MODEL_EMBED"))
        self.num_top_results = 5
        self.text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=250,
            chunk_overlap=30,
            is_separator_regex=False,
        )

    # def __get_text_from_file(self, file_path: str) -> str:
    #     loader = UnstructuredLoader(file_path)
    #     loaded_docs = loader.load()
    #     return "\n\n".join(
    #         doc.page_content
    #         for doc in loaded_docs
    #         if getattr(doc, "page_content", None)
    #     )

    # def _extract_text_from_file(self, file_path: str) -> List[str]:
    #     text_from_file = self.__get_text_from_file(file_path)
    #     splited_texts = self.text_splitter.split_text(text_from_file)
    #     return splited_texts

    # def _get_file_content_based_on_query_text(
    #     self, query: DataForExtraction
    # ) -> DataExtracted:
    #     doc_embeddings = self.model_embed.encode(query.additional_data).astype("float32")

    #     index = faiss.IndexFlatL2(doc_embeddings.shape[1])
    #     index.add(doc_embeddings)

    #     query_embedding = self.model_embed.encode([query.text]).astype("float32")
    #     _, indexes = index.search(query_embedding, self.num_top_results)

    #     founded_context = ""
    #     for ind in indexes[0]:
    #         if ind < len(query.additional_data):
    #             founded_context += query.additional_data[ind] + "\n"

    #     return DataExtracted(text=founded_context)


    def _encode_user_query(query: str) -> List[float]:
        pass


    def _get_most_relevant_text_from_files() -> List[str]:
        pass


    def do_search(self, query: RAGRequest) -> RAGResponse:
        encoded_query = self._encode_user_query(query.text)
        best_text_parts = self._get_most_relevant_text_from_files(encoded_query) # connect to vector db
        return RAGResponse(text=best_text_parts)
