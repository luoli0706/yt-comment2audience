from __future__ import annotations

from .collection_detail_page import collection_detail_view
from .collection_list_page import collection_list_view
from .generate_page import generate_view
from .main_page import main_view
from .portrait_detail_page import portrait_detail_view
from .portrait_list_page import portrait_list_view
from .query_page import query_view

__all__ = [
	"main_view",
	"query_view",
	"generate_view",
	"portrait_detail_view",
	"portrait_list_view",
	"collection_list_view",
	"collection_detail_view",
]
