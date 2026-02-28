"""
ParagraphFactory: Responsible for creating Paragraph objects.
Centralizes all Paragraph instantiation logic.
"""
from typing import Any, Optional

from src.domain.models.paragraph_model import Paragraph


class ParagraphFactory:

    @staticmethod
    def create(
        title: Optional[str],
        sub_title: Optional[str],
        name_doc: str,
        text: str,
        has_table: bool,
        is_article: bool = False,
        table_metadata: list[Any] = None,
    ) -> Paragraph:
        return Paragraph(
            title          = title,
            sub_title      = sub_title,
            name_doc       = name_doc,
            text           = text,
            len_text       = len(text),
            has_table      = has_table,
            is_article     = is_article,
            table_metadata = table_metadata or [],
        )

    @staticmethod
    def create_pre_heading(
        active_title: Optional[str],
        page_header: str,
        name_doc: str,
        text: str,
        has_table: bool,
        table_metadata: list[Any] = None,
    ) -> Paragraph:
        return ParagraphFactory.create(
            title          = active_title,
            sub_title      = page_header,
            name_doc       = name_doc,
            text           = text,
            has_table      = has_table,
            is_article     = False,
            table_metadata = table_metadata,
        )

    @staticmethod
    def create_workflow(
        active_title: Optional[str],
        workflow_title: Optional[str],
        name_doc: str,
        text: str,
        has_table: bool,
        table_metadata: list[Any] = None,
    ) -> Paragraph:
        return ParagraphFactory.create(
            title          = active_title,
            sub_title      = workflow_title,
            name_doc       = name_doc,
            text           = text,
            has_table      = has_table,
            is_article     = False,
            table_metadata = table_metadata,
        )

    @staticmethod
    def create_article(
        active_title: Optional[str],
        sub_title: Optional[str],
        name_doc: str,
        text: str,
        has_table: bool,
        table_metadata: list[Any] = None,
    ) -> Paragraph:
        return ParagraphFactory.create(
            title          = active_title,
            sub_title      = sub_title,
            name_doc       = name_doc,
            text           = text,
            has_table      = has_table,
            is_article     = True,
            table_metadata = table_metadata,
        )