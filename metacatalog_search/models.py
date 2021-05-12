import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import TSVECTOR, ARRAY


Base = declarative_base()


class TSIndex(Base):
    """
    """
    __tablename__ = 'ts_index'

    # columns
    id = sa.Column(sa.BigInteger, primary_key=True)
    attribute_names = sa.Column(ARRAY(sa.String(60)), nullable=False)
    tokens = sa.Column(TSVECTOR, nullable=False)


def merge_declarative_base(other: sa.MetaData):
    """
    Merge this declarative base with metacatalog declarative base
    to enable foreign keys and relationships between both classes.
    """
    # build missing columns
    _connect_to_metacatalog()

    # add these tables to the other metadata
    TSIndex.__table__.to_metadata(other)

    # add relationships
    TSIndex.entry = relationship('Entry')


def _connect_to_metacatalog():
    """
    Call this method to creates missing columns and foreign keys.
    """
    # add the two foreign keys to Entry
    # we need to check if the columns are already there, as the extension might already
    # be loaded by metacatalog and the connection is already there
    if not hasattr(TSIndex, 'entry_id'):
        TSIndex.entry_id  = sa.Column(sa.Integer, sa.ForeignKey('entries.id'), nullable=False)
