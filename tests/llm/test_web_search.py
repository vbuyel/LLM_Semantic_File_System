import sys

# Mock langchain_community before importing
_original_modules = {}
for _key in ["langchain_community", "langchain_community.tools", "langchain_community.tools.DuckDuckGoSearchRun"]:
    _original_modules[_key] = sys.modules.get(_key)

from unittest.mock import MagicMock as _MagicMock
_mock = _MagicMock()
_mock.tools = _MagicMock()
sys.modules["langchain_community"] = _mock
sys.modules["langchain_community.tools"] = _mock.tools
sys.modules["langchain_community.tools.DuckDuckGoSearchRun"] = _MagicMock()

from src.llm.adapters.web_search import WebSearch
from src.llm.domain.domain import SearchResponse

# Restore
for _key, _val in _original_modules.items():
    if _val is None:
        if _key in sys.modules:
            del sys.modules[_key]
    else:
        sys.modules[_key] = _val

import pytest
from unittest.mock import patch, MagicMock
