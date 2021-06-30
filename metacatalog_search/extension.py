from typing import Union, List
from sqlalchemy.orm import object_session
from sqlalchemy import insert, update, delete, exists
from sqlalchemy import func
from sqlalchemy import event
from metacatalog.ext.base import MetacatalogExtensionInterface
from metacatalog.models import Entry
from metacatalog import api

from metacatalog_search import models
from metacatalog_search.api import search, reindex_search
from metacatalog_search.util import expand_dict_to_str


DEFAULT_ATTRIBUTES = ['title', 'abstract', 'comment', 'variable', 'authors', 'keywords', 'details']


def create_search_index(
    self: Entry,
    attributes: Union[str, List[str]] = 'default',
    if_exists = 'replace',
    commit=True,
    ):
    """
    (Re-)create full-text search vectors for this Entry. 
    Tokenized word stems are created for each attribute given and stored.
    Only indexed Entries can be found by the :func:`search API <metacatalog.api.search>`.

    .. note:: 
        This method is part of the `metacatalog-search Extension <https://github.com/vforwater/metacatalog-search>`_
        You need to install and activate the extension, before you can use it.

        .. code-block:: bash
            pip install metacatalog-search
        
        >> from metacatalog import ext
        >> ext.activate_extension('search', 'metacatalog_search.extension', 'SearchExtension')

    Parameters
    ----------
    attributes : list
        List of attribute names that will be indexed. Instead of a list, 
        a string literal can be passed. With ``'default'``, a pre-defined list
        will be used. If ``'all'``, any string-based attribute will be used.
    if_exists : str
        If a Entry already was indexed, if will by default be replaced. 
        With ``'omit'``, the re-index will be skipped and the model is returned.
        If ``'raise'`` a :any:`AttributeError` will be raised. 
    commit : bool
        If True, the created or updated full text search index will be directly
        added to thedatabase. If False, the method will return the respective
        SQL statement.

    """
    # get a session
    session = object_session(self)

    # here, we will need the Table object, not the ORM class
    table = models.TSIndex.__table__

    # check if there is already an index
    is_indexed = session.query(exists().where(models.TSIndex.entry_id == self.id)).scalar()

    # return or raise if already exists and not replace 
    if is_indexed and if_exists == 'raise':
        raise AttributeError(f'The Entry of ID={self.id} was already indexed.')
    elif is_indexed and if_exists == 'omit':
        return session.query(models.TSIndex).where(models.TSIndex.entry_id == self.id).one()

    # we will either insert or update
    if is_indexed:
        stmt = update(table).where(table.c.entry_id == self.id)
    else:
        stmt = insert(table)

    # handles the attributes list
    if attributes == 'default':
        attributes = DEFAULT_ATTRIBUTES
    if not isinstance(attributes, list) or any([not isinstance(_, str) for _ in attributes]):
        raise AttributeError(f"attributes has to be a list of names.")
    
    # collect all text chunks
    text_chunks = []
    attribute_names = []

    # collect the index information
    for name in attributes:
        if hasattr(self, name):
            text_chunks.extend(expand_dict_to_str(getattr(self, name)))
            attribute_names.append(name)
    
    # check if something was collected
    if len(text_chunks) == 0 or all([_ == '' for _ in text_chunks]):
        raise ValueError(f"This Entry cannot be indexed. No Strings found in {attributes}")
    
    # create the model
    stmt = stmt.values({
        'entry_id': self.id,
        'attribute_names': attribute_names,
        'tokens': func.to_tsvector(SearchExtension.LANGUAGE, ' '.join(text_chunks))
    })

    if not commit:
        return stmt

    # commit
    try:
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e


def after_entry_insert(mapper, connection, target: Entry):
    """
    Call 
    """
    # TODO this is not yet working
    # get the correct statement
    # TODO how to handle the attributes list here?
#    stmt = target.create_search_index(commit=False)

    # execute
#    connection.execute(stmt)


def after_entry_update(mapper, connection, target: Entry):
    """
    Re-index the Entry after update
    """
    # TODO make this work again somehow
    # get the the update statement
#    stmt = target.create_search_index(commit=False)
#    connection.execute(stmt)


def before_entry_delete(mapper, connection, target: Entry):
    """
    Delete the search index before the Entry is deleted
    """
    stmt = delete(models.TSIndex).where(models.TSIndex.entry_id==target.id)
    connection.execute(stmt)


class SearchExtension(MetacatalogExtensionInterface):
    """
    Full Text Search extension. 
    This extension enables Metacatalog to search the database by
    PostgreSQL full-text search capabilities. A new table is installed
    to the database that indexes tokenized word stems for any specified
    text based attribute of the Entry.

    It adds a new instance method to Entry, to create a new search index
    for that specific Entry. Additionally, two API functions are added.
    A function to search and another function to re-index the whole table.

    Finally, new event listeners are added, that will re-create the search 
    index on Entry insert and update query. 

    """
    # TODO how to handle these settings better?
    LANGUAGE = 'english'
    AUTOINDEX = True

    @classmethod
    def init_extension(cls):
        """
        """
        # merge the declarative base from metacatalog
        from metacatalog.db.base import Base
        models.merge_declarative_base(Base.metadata)

        # add new instance method to Entry
        Entry.create_search_index = create_search_index

        # add new methods to API - check if this is working
        api.search = search
        api.reindex_search = reindex_search

        # TODO: add new event to index to Entry
        if cls.AUTOINDEX:
            event.listen(Entry, 'after_insert', after_entry_insert)
            event.listen(Entry, 'after_update', after_entry_update)

        #  add delete event to Entry
        event.listen(Entry, 'before_delete', before_entry_delete)
        