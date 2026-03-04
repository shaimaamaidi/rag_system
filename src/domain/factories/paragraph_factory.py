"""Factory helpers for creating :class:`Paragraph` instances."""
from typing import Any, Optional

from src.domain.models.paragraph_model import Paragraph


class ParagraphFactory:
    """Create :class:`Paragraph` objects with consistent defaults."""

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
        """Create a paragraph instance.

        :param title: Section title.
        :param sub_title: Subsection title.
        :param name_doc: Document name.
        :param text: Paragraph text.
        :param has_table: Whether the paragraph contains a table.
        :param is_article: Whether this paragraph represents an article.
        :param table_metadata: Table metadata list.
        :return: Paragraph instance.
        """
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
        """Create a paragraph for pre-heading content.

        :param active_title: Active document title.
        :param page_header: Page header used as subtitle.
        :param name_doc: Document name.
        :param text: Paragraph text.
        :param has_table: Whether the paragraph contains a table.
        :param table_metadata: Table metadata list.
        :return: Paragraph instance.
        """
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
        """Create a paragraph for workflow content.

        :param active_title: Active document title.
        :param workflow_title: Workflow title used as subtitle.
        :param name_doc: Document name.
        :param text: Paragraph text.
        :param has_table: Whether the paragraph contains a table.
        :param table_metadata: Table metadata list.
        :return: Paragraph instance.
        """
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
        """Create a paragraph marked as an article.

        :param active_title: Active document title.
        :param sub_title: Subsection title.
        :param name_doc: Document name.
        :param text: Paragraph text.
        :param has_table: Whether the paragraph contains a table.
        :param table_metadata: Table metadata list.
        :return: Paragraph instance.
        """
        return ParagraphFactory.create(
            title          = active_title,
            sub_title      = sub_title,
            name_doc       = name_doc,
            text           = text,
            has_table      = has_table,
            is_article     = True,
            table_metadata = table_metadata,
        )