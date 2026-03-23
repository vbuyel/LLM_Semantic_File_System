import os
from langchain_text_splitters import CharacterTextSplitter
from langchain_unstructured import UnstructuredLoader
# from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from openai import OpenAI
from typing import List

from numpy import float32
import faiss
from src.llm.agent_web_rag.domain.domain import DataForExtraction, DataExtracted, RAGRequest, RAGResponse
from sentence_transformers import SentenceTransformer

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


    def __get_text_from_file(self, file_path: str) -> str:
        loader = UnstructuredLoader(file_path)
        loaded_docs = loader.load()
        return "\n\n".join(doc.page_content for doc in loaded_docs if getattr(doc, "page_content", None))


    def _extract_text_from_file(self, file_path: str) -> List[str]:
        text_from_file = self.__get_text_from_file(file_path)
        splited_texts = self.text_splitter.split_text(text_from_file)
        return splited_texts


    def _get_file_content_based_on_query_text(self, query: DataForExtraction) -> DataExtracted:
        docs_embed = self.model_embed.encode(query.additional_data).astype(float32)
        index = faiss.IndexFlatL2(docs_embed.shape[1])

        index.add(docs_embed)
        query_text_embed = self.model_embed.encode([query.text]).astype(float32)

        _, indexes = index.search(query_text_embed, self.num_top_results)

        founded_context = ""
        for ind in indexes[0]:
            founded_context += query.additional_data[ind] + "\n"
        
        return DataExtracted(text=founded_context)


    def do_search(self, query: RAGRequest) -> RAGResponse:
        query.additional_data = self._extract_text_from_file(query.additional_data)
        file_content = self._get_file_content_based_on_query_text(DataForExtraction(text=query.text, additional_data=query.additional_data))
        return RAGResponse(text=file_content.text)
