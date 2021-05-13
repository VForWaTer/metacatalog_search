from typing import Union, List
import sqlalchemy as sa
from sqlalchemy import func
from tqdm import tqdm

from metacatalog.models import Entry
from metacatalog_search.models import TSIndex


def search(
        session: sa.orm.Session,
        search_string: str,
        limit: int = None,
        query: sa.orm.Query = None,
        as_result=False,
        return_iterator=False
    ):
    """
    Perform a full text search on the database.

    .. note:: 
        This method is part of the `metacatalog-search Extension <https://github.com/vforwater/metacatalog-search>`_
        You need to install and activate the extension, before you can use it.

        .. code-block:: bash
            pip install metacatalog-search
        
        >> from metacatalog import ext
        >> ext.activate_extension('search', 'metacatalog_search.extension', 'SearchExtension')

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Session connected to the database of metacatalog
    search_string : str
        The pattern to be searched. The search string can contain more
        than a single term and terms can be combined using logical expressions
        like or: ``'|'``, and: ``'&'`` or not: ``'!'``
    limit : int
        If given, the search results will be limited.

        .. note::
            Right now, the result is not yet sorted by relevance. Hence, 
            a limit will **not** necessarily return the most relevant 
            search results.

    query : sa.orm.Query
        Optionally, a base query can be passed, that may already contain
        filters. If not passed, it defaults to return a list of
        :class:`Entries <metacatalog.models.Entry>`
    as_result : bool
        If True, the result will be wrapped by a list of
        :class:`ImmutableResultSets <metcatalog.util.results.ImmutableResultSet>`.
    return_iterator : bool
        If True the query will be returned, instead of the results.
        Defaults to False.

    """
    # import here, due to circular imports
    from metacatalog_search.extension import SearchExtension
    # check if a base query was passed
    if query is None:
        query = session.query(Entry).join(TSIndex)
    else:
        query = query.join(TSIndex)
    
    # Add the full text search filter
    query = query.filter(TSIndex.tokens.match(f"'{search_string}'", postgresql_regconfig=SearchExtension.LANGUAGE))

    # TODO: here we could do a order by relevance somehow

    # add limit if needed
    if limit is not None:
        query = query.limit(limit)

    # return logic
    if return_iterator:
        return query
    else:
        if as_result:
            # import here due to circular imports
            from metacatalog.util.results import ImmutableResultSet
            return [ImmutableResultSet(entry) for entry in query.all()]
        return query.all()


def reindex_search(
    session: sa.orm.Session, 
    entries: Union[str, List[int], List[Entry]],
    attributes: Union[str, List[str]],
    if_exists = 'replace',
    verbose = False
    ):
    """
    Reindex the given list of :class:`Entries <metacatalog.models.Entry>`
    for full text search. The entries can be given as a List of ORM models
    as returned by the :func`find_entry <metacatalog.api.find_entry>` API
    or a list of thier ids. Finally, ``'all'`` or ``'missing'`` entries
    can be specified as a string literal.

    .. note:: 
        This method is part of the `metacatalog-search Extension <https://github.com/vforwater/metacatalog-search>`_
        You need to install and activate the extension, before you can use it.

        .. code-block:: bash
            pip install metacatalog-search
        
        >> from metacatalog import ext
        >> ext.activate_extension('search', 'metacatalog_search.extension', 'SearchExtension')

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Session connected to the database of metacatalog
    entries : list
        List of Entries, their ids or the literal ``'all'`` or 
        ``'missing'``. Be careful with literals as they might
        take some substantial amout of time.
    attributes : list
        List of attribute names that will be indexed. Instead of a list, 
        a string literal can be passed. With ``'default'``, a pre-defined list
        will be used. If ``'all'``, any string-based attribute will be used.
    if_exists : str
        If a Entry already was indexed, if will by default be replaced. 
        With ``'omit'``, the re-index will be skipped and the model is returned.
        If ``'raise'`` a :any:`AttributeError` will be raised.
    verbose : bool
        If True, a progressbar will be displayed. Defaults to False.

    """
    # check the entries attribute
    if entries == 'all':
        entry_stream = session.query(Entry)
    elif entries == 'missing':
        indexed_ids = [id for id, in session.query(TSIndex.entry_id)]
        entry_stream = session.query(Entry).filter(Entry.id.notin_(indexed_ids))
    elif isinstance(entries, sa.orm.query.Query):
        entry_stream = entries
    elif all([isinstance(_, int) for _ in entries]):
        entry_stream = session.query(Entry).filter(Entry.id.in_(entries))
    elif all([isinstance(_, Entry) for _ in entries]):
        entry_stream = entries
    else:
        raise AttributeError('entries not given as supported format.')
    
    # handle verbosity
    if verbose:
        if hasattr(entry_stream, 'count'):
            l = entry_stream.count()
        else:
            l = len(entry_stream)
        entry_stream = tqdm(entry_stream, total=l)
    
    # start the indexing
    # TODO: this could be run in parallel 
    for entry in entry_stream:
        entry.create_search_index(attributes=attributes, if_exists=if_exists)
