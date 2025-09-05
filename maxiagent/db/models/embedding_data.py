from sqlalchemy import Column, Text, UUID, DateTime, func
from pgvector.sqlalchemy import Vector

from ..database import Base

class EmbeddingData(Base):
    __tablename__: str = 'tb_mk_embedding_data'
    __table_args__: dict[str, str] = {'comment': 'Stores event embeddings with vector representations'}
    
    event_uuid = Column(UUID(as_uuid=True), primary_key=True)
    embedding_data_text = Column(Text, nullable=False)
    embedding_embedded_text = Column(Vector(768), nullable=False)
    embedding_timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )