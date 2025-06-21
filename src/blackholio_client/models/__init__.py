"""
Models Module - Unified Game Data Models

Consolidates data models from blackholio-agent and client-pygame
into consistent, reusable classes with comprehensive serialization,
validation, and protocol adaptation support for all SpacetimeDB
server languages.
"""

from .game_entities import (
    Vector2,
    GameEntity,
    GamePlayer,
    GameCircle,
    EntityType,
    PlayerState
)
from .data_converters import (
    DataConverter,
    EntityConverter,
    PlayerConverter,
    CircleConverter,
    convert_to_entity,
    convert_to_player,
    convert_to_circle,
    convert_to_dict
)
from .physics import (
    calculate_center_of_mass,
    calculate_distance,
    calculate_entity_radius,
    check_collision,
    find_nearest_entity,
    interpolate_position
)
from .game_statistics import (
    PlayerStatistics,
    SessionStatistics,
    create_player_statistics,
    create_session_statistics
)
from .serialization import (
    SerializationFormat,
    ServerLanguage,
    BaseSerializer,
    JSONSerializer,
    BinarySerializer,
    SerializerRegistry,
    serialize,
    deserialize,
    get_serializer,
    SerializationError,
    DeserializationError
)
from .schemas import (
    SchemaManager,
    DataValidator,
    ValidationError,
    validate_entity,
    validate_player,
    validate_circle,
    validate_vector,
    validate_game_state,
    get_schema,
    register_schema,
    list_available_schemas
)
from .protocol_adapters import (
    ProtocolVersion,
    ProtocolAdapter,
    RustProtocolAdapter,
    PythonProtocolAdapter,
    CSharpProtocolAdapter,
    GoProtocolAdapter,
    ProtocolAdapterRegistry,
    adapt_to_server,
    adapt_from_server,
    get_protocol_adapter,
    register_custom_adapter
)
from .data_pipeline import (
    DataPipeline,
    PipelineConfiguration,
    ProcessingMetrics,
    ProcessingError,
    process_for_server,
    process_from_server,
    create_pipeline,
    get_global_pipeline
)

__all__ = [
    # Game entities
    "Vector2",
    "GameEntity", 
    "GamePlayer",
    "GameCircle",
    "EntityType",
    "PlayerState",
    
    # Data converters
    "DataConverter",
    "EntityConverter",
    "PlayerConverter",
    "CircleConverter",
    "convert_to_entity",
    "convert_to_player",
    "convert_to_circle",
    "convert_to_dict",
    
    # Physics calculations
    "calculate_center_of_mass",
    "calculate_distance",
    "calculate_entity_radius",
    "check_collision",
    "find_nearest_entity",
    "interpolate_position",
    
    # Statistics tracking
    "PlayerStatistics",
    "SessionStatistics",
    "create_player_statistics",
    "create_session_statistics",
    
    # Serialization system
    "SerializationFormat",
    "ServerLanguage",
    "BaseSerializer",
    "JSONSerializer",
    "BinarySerializer",
    "SerializerRegistry",
    "serialize",
    "deserialize",
    "get_serializer",
    "SerializationError",
    "DeserializationError",
    
    # Schema validation
    "SchemaManager",
    "DataValidator",
    "ValidationError",
    "validate_entity",
    "validate_player",
    "validate_circle",
    "validate_vector",
    "validate_game_state",
    "get_schema",
    "register_schema",
    "list_available_schemas",
    
    # Protocol adapters
    "ProtocolVersion",
    "ProtocolAdapter",
    "RustProtocolAdapter",
    "PythonProtocolAdapter",
    "CSharpProtocolAdapter",
    "GoProtocolAdapter",
    "ProtocolAdapterRegistry",
    "adapt_to_server",
    "adapt_from_server",
    "get_protocol_adapter",
    "register_custom_adapter",
    
    # Data pipeline
    "DataPipeline",
    "PipelineConfiguration",
    "ProcessingMetrics",
    "ProcessingError",
    "process_for_server",
    "process_from_server",
    "create_pipeline",
    "get_global_pipeline",
]
