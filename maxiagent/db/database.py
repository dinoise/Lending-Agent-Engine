from ..utils import get_secret
from ..config import current_config

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from sqlalchemy.engine import Engine

from urllib.parse import quote_plus
from typing import Dict, Any

# Bases declarativas para cada base de datos
Base = declarative_base()
BaseMetadata = declarative_base()

# Diccionarios para almacenar los engines y sesiones
engines: Dict[str, Any] = {}
db_sessions: Dict[str, Any] = {}

def init_db() -> None:
    # Configuración para la base de datos primaria
    configure_database('rag_corpus_maxikash', {
        'PG_HOST': get_secret(current_config.PG_HOST),
        'PG_PORT': get_secret(current_config.PG_PORT),
        'PG_USER': get_secret(current_config.PG_USER),
        'PG_PASSWORD': get_secret(current_config.PG_PASSWORD),
        'PG_NAME': get_secret(current_config.PG_NAME)
    }, Base)

def configure_database(db_name: str, config: dict, base) -> None:
    global engines, db_sessions
    
    PG_HOST = config['PG_HOST']
    PG_PORT = config['PG_PORT']
    PG_USER = config['PG_USER']
    PG_PASSWORD = config['PG_PASSWORD']
    PG_NAME = config['PG_NAME']

    if not all([PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_NAME]):
        raise ValueError(f"Faltan valores de configuración para la base de datos {db_name}")

    encoded_pg_password = quote_plus(PG_PASSWORD)
    uri: str = f'postgresql+psycopg2://{PG_USER}:{encoded_pg_password}@{PG_HOST}:{PG_PORT}/{PG_NAME}'

    try:
        engines[db_name] = create_engine(uri)
        
        # Configura la sesión
        db_sessions[db_name] = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engines[db_name]
        ))
        
        # Conecta la Base con el engine
        base.metadata.bind = engines[db_name]
        
        # Prueba la conexión
        with engines[db_name].connect() as conn:
            print(f"✅ Conexión a la base de datos {db_name} establecida correctamente")
            
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos {db_name}: {e}")
        raise

# Funciones para obtener sesiones específicas
def get_db_session(db_name='rag_corpus_maxikash') -> scoped_session:
    if db_name not in db_sessions:
        raise RuntimeError(f"La base de datos {db_name} no ha sido inicializada. Llama a init_db() primero.")
    return db_sessions[db_name]

def get_engine(db_name='poc_data') -> Engine:
    if db_name not in engines:
        raise RuntimeError(f"El engine para {db_name} no ha sido inicializado. Llama a init_db() primero.")
    return engines[db_name]