from typing import List
import uuid

from maxiagent.db import get_db_session
from maxiagent.db import EmbeddingData

from os import getenv
from dotenv import load_dotenv
from langchain_google_vertexai import VertexAIEmbeddings

load_dotenv()

def ingest_single_embedding(
    text: str
) -> EmbeddingData:
    """
    Genera e ingesta un embedding individual
    
    Args:
        text: Texto para generar embedding
        target_dataset: Dataset destino
        target_table: Tabla destino
        metadata: Metadatos adicionales
    
    Returns:
        Objeto EmbeddingData creado
    """
    db = get_db_session()
    if not db:
        raise Exception("Inicializa la base de datos primero")
    
    try:
        # Generar embedding
        embedding_service = VertexAIEmbeddings(
            model_name=getenv("EMBEDDING_MODEL_NAME")
        )
        embedding: List[float] = embedding_service.embed_query(text)
        
        # Crear objeto
        embedding_obj = EmbeddingData(
            event_uuid=uuid.uuid4(),
            embedding_data_text=text,
            embedding_embedded_text=embedding
        )
        
        # Guardar en BD
        db.add(embedding_obj)
        db.commit()
        
        return embedding_obj
    except Exception as e:
        db.rollback()
        raise Exception(f"Error ingiriendo embedding: {str(e)}")
    finally:
        db.close()


text = """"
Documento 3: Preguntas Frecuentes (Las Dudas más
Comunes)
P: ¿Cuánto se tardan en todo el rollo? Desde que pido el crédito
hasta que tengo la moto.
R: Somos los más rápidos, la neta. En lo que te echas dos o tres pedidos, nosotros ya te
dimos respuesta de tu crédito (en 2 horas o menos). Y en menos de lo que dura una semana
de chamba, ya tienes la moto contigo, lista para generar más lana.
P: ¿Y cómo pago mis abonos o veo cuánto debo?
R: Todo lo manejas desde la app deMaxikash. Para pagar en OXXO, por ejemplo, solo abres
la app, eliges "Pagar en OXXO"
, te genera un código de barras, se lo enseñas al cajero, pagas
y ¡listo! En minutos se refleja en tu cuenta y te llega una notificación. Es fácil, rápido y seguro.
P: ¿Qué pasa si una semana se me complica y no puedo pagar?
R: ¡Habla con nosotros! La comunicación es clave. Entendemos que hay semanas buenas y
malas, que a veces la moto necesita una reparación o simplemente no hubo tanta chamba. Lo
más importante es que te comuniques con nosotros ANTES de tu fecha de pago. Búscanos en
la app y vemos qué solución te podemos dar. Podemos darte chance una semana y que
pagues dos abonos juntos la siguiente, o buscar otra opción. No te escondas, un cliente que
da la cara siempre tiene nuestro apoyo.
P: ¿Puedo cambiar mi día de pago semanal?
R: Sí se puede, claro. Nos adaptamos a tu ritmo de trabajo. Si antes repartías más los fines de
semana y te convenía pagar los lunes, pero ahora tu día bueno es el miércoles, contáctanos
por la app. Hacemos el ajuste para que tu nueva fecha de pago sea el jueves y así no te
agarren las prisas.
P: ¿La moto tiene garantía?
R: ¡Claro! Tu moto es completamente nueva y sale de una agencia autorizada. Tiene la
garantía que ofrece la marca (Italika, Vento o Bajaj), que usualmente cubre el motor y partes
importantes por un tiempo o kilometraje determinado. Ojo, la garantía es para fallas de
fábrica, no cubre piezas de desgaste normal como llantas, balatas, cadena, o si te caes. Por
eso es importante que la cuides y le hagas sus servicios a tiempo.
P: ¿A fuerza necesito seguro para la moto?
R: Sí, es a fuerza y es por tu bien y el nuestro. Piénsalo así: tu moto es tu herramienta de
trabajo, es la que te da de comer. Si te la roban, no solo te quedas sin moto, te quedas sin
chamba y con una deuda. El seguro de cobertura amplia te quita ese broncón de encima. Si
algo pasa, el seguro paga la deuda y tú no pierdes todo. Es una inversión en tu tranquilidad y
en la seguridad de tu negocio.
P: ¿Puedo sacar otra moto si termino de pagar esta?
R: ¡Por supuesto! Un cliente que paga bien es un cliente que queremos conservar. En cuanto
termines de pagar tu crédito, puedes solicitar otro. Y como ya te conocemos y sabemos que
eres cumplidor, es muy probable que te ofrezcamos una tasa de interés todavía más baja o
mejores condiciones.
P: ¿El crédito incluye el casco o el equipo de seguridad?
R: El crédito está calculado para el costo de la motocicleta. Sin embargo, tu seguridad es lo
más importante. Si necesitas una lana extra para un buen casco certificado, una chamarra
con protecciones o un impermeable, platícalo con tu asesor. A veces podemos aumentar un
poco el monto de tu crédito para que salgas a la calle bien protegido desde el primer día.
"""


data = ingest_single_embedding(text)

print(data)