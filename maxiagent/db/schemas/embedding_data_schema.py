from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models.embedding_data import EmbeddingData
from marshmallow import fields, ValidationError
import numpy as np

class VectorField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return []
        # Convertir cada elemento a float nativo de Python
        return [float(x) for x in value]

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, list):
            raise ValidationError("El campo debe ser una lista de números.")
        try:
            # Convertir cada elemento a float32 de numpy
            return np.array([float(x) for x in value], dtype=np.float32)
        except (ValueError, TypeError):
            raise ValidationError("Todos los elementos deben ser números válidos.")

class EmbeddingDataSchema(SQLAlchemyAutoSchema):
    embedding_embedded_text = VectorField()

    class Meta:
        model = EmbeddingData
        only: tuple = ('embedding_embedded_text',)