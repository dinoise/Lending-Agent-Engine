from ..utils import get_secret
from ..config import current_config

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from sqlalchemy.engine import Engine

from urllib.parse import quote_plus

# Bases declarativas para cada base de datos
Base = declarative_base()
BaseMetadata = declarative_base()

# Diccionarios para almacenar los engines y sesiones
engine: Engine | None = None
db_session: scoped_session | None = None

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
    global engine, db_session
    
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
        engine = create_engine(
            uri,
            connect_args={'options': f'-c search_path=public'}
)
        
        # Configura la sesión
        db_session = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        ))
        
        # Conecta la Base con el engine
        base.metadata.bind = engine
        
        # Prueba la conexión
        with engine.connect() as conn:
            print(f"✅ Conexión a la base de datos {db_name} establecida correctamente")
            
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos {db_name}: {e}")
        raise

# Funciones para obtener sesiones específicas
def get_db_session(db_name='rag_corpus_maxikash') -> scoped_session | None:
    if not db_session:
        raise RuntimeError(f"La base de datos {db_name} no ha sido inicializada. Llama a init_db() primero.")
    return db_session

def get_engine(db_name='rag_corpus_maxikash') -> Engine | None:
    if not engine:
        raise RuntimeError(f"El engine para {db_name} no ha sido inicializado. Llama a init_db() primero.")
    return engine