"""
Protocol Handlers - SpacetimeDB Protocol Processing

Handles different SpacetimeDB protocol versions and message processing.
Currently supports v1.1.2 protocol with extensibility for future versions.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


logger = logging.getLogger(__name__)


class ProtocolHandler(ABC):
    """
    Abstract base class for SpacetimeDB protocol handlers.
    
    Allows for different protocol versions to be supported
    with consistent interfaces.
    """
    
    @abstractmethod
    def process_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process incoming message from SpacetimeDB.
        
        Args:
            data: Raw message data from server
            
        Returns:
            Processed message data or None if message should be ignored
        """
        pass
    
    @abstractmethod
    def format_outgoing_message(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format outgoing message for SpacetimeDB.
        
        Args:
            message_type: Type of message to send
            data: Message data
            
        Returns:
            Formatted message ready for transmission
        """
        pass


class V112ProtocolHandler(ProtocolHandler):
    """
    SpacetimeDB v1.1.2 protocol handler.
    
    Consolidates the v1.1.2 protocol handling logic from both
    blackholio-agent and client-pygame implementations.
    """
    
    def __init__(self):
        self.protocol_version = "v1.1.2"
        self.message_handlers = {
            'TransactionUpdate': self._handle_transaction_update,
            'TransactionCommit': self._handle_transaction_commit,
            'SubscriptionUpdate': self._handle_subscription_update,
            'DatabaseUpdate': self._handle_database_update,
            'Error': self._handle_error,
            'Connected': self._handle_connected,
            'Disconnected': self._handle_disconnected,
            'IdentityToken': self._handle_identity_token,
        }
        
        logger.debug(f"Initialized {self.protocol_version} protocol handler")
    
    def process_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process v1.1.2 protocol message.
        
        Consolidates message processing logic from both existing implementations.
        """
        try:
            # Debug: Log object types for troubleshooting
            if 'database_update' in data:
                db_update = data['database_update']
                logger.debug(f"DatabaseUpdate type: {type(db_update)}, attrs: {dir(db_update)}")
            
            # Determine message type
            message_type = self._get_message_type(data)
            
            if not message_type:
                # Enhanced debugging for unknown messages
                logger.warning(f"Unknown message type in data keys: {list(data.keys())}")
                for key, value in data.items():
                    logger.debug(f"  {key}: {type(value)} = {str(value)[:100]}...")
                return None
            
            # Process with appropriate handler
            if message_type in self.message_handlers:
                return self.message_handlers[message_type](data)
            else:
                logger.warning(f"No handler for message type: {message_type}")
                return self._handle_unknown_message(data)
                
        except AttributeError as e:
            logger.error(f"AttributeError in message processing: {e}")
            logger.debug(f"Data structure: {data}")
            return None
        except Exception as e:
            logger.error(f"Error processing v1.1.2 message: {e}")
            logger.debug(f"Full data: {data}")
            return None
    
    def format_outgoing_message(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format outgoing message for v1.1.2 protocol.
        
        CRITICAL: SpacetimeDB does NOT accept custom "type" fields in JSON messages.
        Only specific protocol-compliant message formats are allowed.
        """
        # IMPORTANT: Do not add arbitrary fields like 'type', 'protocol', or 'timestamp'
        # SpacetimeDB protocol has specific message formats that must be followed
        
        # For now, just return the data as-is
        # The actual formatting should be done by the SDK's protocol helper
        return data
    
    def _safe_extract(self, obj, attr_name, default=None):
        """Safely extract attribute from object or dict"""
        if obj is None:
            return default
        
        # Try attribute access first (for objects)
        if hasattr(obj, attr_name):
            return getattr(obj, attr_name)
        
        # Fall back to dict access
        if isinstance(obj, dict):
            return obj.get(attr_name, default)
        
        return default

    def _extract_nested_value(self, obj, path, default=None):
        """Extract nested values like obj.nanos.micros"""
        current = obj
        for part in path:
            current = self._safe_extract(current, part)
            if current is None:
                return default
        return current
    
    def _get_message_type(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract message type from incoming data."""
        # Try different possible message type fields
        type_fields = ['type', 'message_type', 'event', 'kind']
        
        for field in type_fields:
            if field in data:
                return data[field]
        
        # Handle transaction commit responses
        if 'status' in data and 'timestamp' in data and 'caller_identity' in data:
            return 'TransactionCommit'
        
        # Handle identity token responses
        if 'identity' in data and 'token' in data and 'connection_id' in data:
            return 'IdentityToken'
        
        # Handle database update responses
        if 'database_update' in data and 'request_id' in data:
            return 'DatabaseUpdate'
        
        # Check for specific v1.1.2 patterns
        if 'transaction_update' in data:
            return 'TransactionUpdate'
        elif 'subscription_update' in data:
            return 'SubscriptionUpdate'
        elif 'error' in data:
            return 'Error'
        elif 'status' in data:
            status = data.get('status', '').lower()
            if 'connected' in status:
                return 'Connected'
            elif 'disconnected' in status:
                return 'Disconnected'
        
        return None
    
    def _handle_transaction_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle transaction update messages.
        
        Consolidates transaction update handling from both projects.
        """
        try:
            # Extract transaction data
            transaction_data = data.get('transaction_update', data)
            
            # Process table updates
            table_updates = []
            if 'tables' in transaction_data:
                for table_name, table_data in transaction_data['tables'].items():
                    table_updates.append({
                        'table': table_name,
                        'data': table_data,
                        'operation': table_data.get('operation', 'update')
                    })
            
            # Process entity updates (common pattern from both projects)
            entities = []
            players = []
            circles = []
            
            for update in table_updates:
                table_name = update['table'].lower()
                table_data = update['data']
                
                if 'entity' in table_name or 'object' in table_name:
                    entities.extend(self._extract_entities(table_data))
                elif 'player' in table_name:
                    players.extend(self._extract_players(table_data))
                elif 'circle' in table_name:
                    circles.extend(self._extract_circles(table_data))
            
            return {
                'type': 'transaction_update',
                'timestamp': data.get('timestamp'),
                'entities': entities,
                'players': players,
                'circles': circles,
                'raw_updates': table_updates
            }
            
        except Exception as e:
            logger.error(f"Error handling transaction update: {e}")
            return {
                'type': 'transaction_update',
                'error': str(e),
                'raw_data': data
            }
    
    def _handle_subscription_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription update messages."""
        try:
            # Handle case where data might be a SubscriptionUpdate object
            if hasattr(data, '__class__') and 'Subscription' in data.__class__.__name__:
                return {
                    'type': 'subscription_update',
                    'status': getattr(data, 'status', 'unknown'),
                    'tables': getattr(data, 'tables', []),
                    'timestamp': getattr(data, 'timestamp', None)
                }
            elif isinstance(data, dict) and 'data' in data:
                # Handle wrapped object case
                sub_obj = data.get('data')
                if hasattr(sub_obj, 'status'):
                    return {
                        'type': 'subscription_update',
                        'status': getattr(sub_obj, 'status', 'unknown'),
                        'tables': getattr(sub_obj, 'tables', []),
                        'timestamp': getattr(sub_obj, 'timestamp', None)
                    }
            
            # Original dictionary handling
            if isinstance(data, dict):
                subscription_data = data.get('subscription_update', data)
                
                return {
                    'type': 'subscription_update',
                    'status': subscription_data.get('status', 'unknown') if isinstance(subscription_data, dict) else 'unknown',
                    'tables': subscription_data.get('tables', []) if isinstance(subscription_data, dict) else [],
                    'timestamp': data.get('timestamp')
                }
            
            # Fallback for unexpected data types
            logger.warning(f"Unexpected data type in _handle_subscription_update: {type(data)}")
            return {
                'type': 'subscription_update',
                'status': 'unknown',
                'tables': [],
                'timestamp': None
            }
            
        except Exception as e:
            logger.error(f"Error handling subscription update: {e}")
            return {
                'type': 'subscription_update',
                'error': str(e),
                'raw_data': data
            }
    
    def _handle_error(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error messages."""
        # Handle case where data might be an Error object
        if hasattr(data, '__class__') and 'Error' in data.__class__.__name__:
            # data is an Error object directly
            return {
                'type': 'error',
                'message': getattr(data, 'message', 'Unknown error'),
                'code': getattr(data, 'code', None),
                'details': getattr(data, 'details', None),
                'timestamp': getattr(data, 'timestamp', None)
            }
        
        # Original dictionary handling
        if isinstance(data, dict):
            error_data = data.get('error', data)
            
            return {
                'type': 'error',
                'message': error_data.get('message', 'Unknown error') if isinstance(error_data, dict) else str(error_data),
                'code': error_data.get('code') if isinstance(error_data, dict) else None,
                'details': error_data.get('details') if isinstance(error_data, dict) else None,
                'timestamp': data.get('timestamp')
            }
        
        # Fallback for unexpected data types
        logger.warning(f"Unexpected data type in _handle_error: {type(data)}")
        return {
            'type': 'error',
            'message': str(data),
            'code': None,
            'details': None,
            'timestamp': None
        }
    
    def _handle_connected(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connection confirmation messages."""
        # Handle case where data might be a Connected object
        if hasattr(data, '__class__') and 'Connected' in data.__class__.__name__:
            return {
                'type': 'connected',
                'status': getattr(data, 'status', 'connected'),
                'timestamp': getattr(data, 'timestamp', None)
            }
        
        # Original dictionary handling
        if isinstance(data, dict):
            return {
                'type': 'connected',
                'status': data.get('status', 'connected'),
                'timestamp': data.get('timestamp')
            }
        
        # Fallback for unexpected data types
        return {
            'type': 'connected',
            'status': 'connected',
            'timestamp': None
        }
    
    def _handle_disconnected(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disconnection messages."""
        # Handle case where data might be a Disconnected object
        if hasattr(data, '__class__') and 'Disconnected' in data.__class__.__name__:
            return {
                'type': 'disconnected',
                'reason': getattr(data, 'reason', 'Unknown'),
                'timestamp': getattr(data, 'timestamp', None)
            }
        
        # Original dictionary handling
        if isinstance(data, dict):
            return {
                'type': 'disconnected',
                'reason': data.get('reason', 'Unknown'),
                'timestamp': data.get('timestamp')
            }
        
        # Fallback for unexpected data types
        return {
            'type': 'disconnected',
            'reason': 'Unknown',
            'timestamp': None
        }
    
    def _handle_transaction_commit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transaction commit response"""
        # Handle case where data might be a TransactionCommit object
        if hasattr(data, '__class__') and 'TransactionCommit' in data.__class__.__name__:
            # data is a TransactionCommit object directly
            return {
                'type': 'TransactionCommit',
                'status': getattr(data, 'status', None),
                'timestamp': getattr(data, 'timestamp', None),
                'energy_used': getattr(data, 'energy_quanta_used', None),
                'execution_duration': getattr(data, 'total_host_execution_duration', None)
            }
        elif isinstance(data, dict) and 'data' in data:
            # Handle wrapped object case
            commit_obj = data.get('data')
            if hasattr(commit_obj, 'status'):
                return {
                    'type': 'TransactionCommit',
                    'status': getattr(commit_obj, 'status', None),
                    'timestamp': getattr(commit_obj, 'timestamp', None),
                    'energy_used': getattr(commit_obj, 'energy_quanta_used', None),
                    'execution_duration': getattr(commit_obj, 'total_host_execution_duration', None)
                }
        
        # Original dictionary handling
        elif isinstance(data, dict):
            return {
                'type': 'TransactionCommit',
                'status': data.get('status'),
                'timestamp': data.get('timestamp'),
                'energy_used': data.get('energy_quanta_used'),
                'execution_duration': data.get('total_host_execution_duration')
            }
        
        # Fallback for unexpected data types
        else:
            logger.warning(f"Unexpected data type in _handle_transaction_commit: {type(data)}")
            return {
                'type': 'TransactionCommit',
                'status': None,
                'timestamp': None,
                'energy_used': None,
                'execution_duration': None
            }

    def _handle_database_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database update response"""
        # Handle case where data itself is a DatabaseUpdate object
        if hasattr(data, '__class__') and 'DatabaseUpdate' in data.__class__.__name__:
            # data is a DatabaseUpdate object directly
            return {
                'type': 'DatabaseUpdate',
                'tables': getattr(data, 'tables', []),
                'request_id': getattr(data, 'request_id', None),
                'execution_duration': getattr(data, 'total_host_execution_duration', None)
            }
        
        # Handle case where data might contain a DatabaseUpdate object
        elif isinstance(data, dict) and 'data' in data:
            # This happens when the message decoder returns {'type': 'DatabaseUpdate', 'data': <DatabaseUpdate object>}
            database_update_obj = data.get('data')
            if hasattr(database_update_obj, 'tables'):
                # Handle as object with attributes
                return {
                    'type': 'DatabaseUpdate',
                    'tables': getattr(database_update_obj, 'tables', []),
                    'request_id': getattr(database_update_obj, 'request_id', None),
                    'execution_duration': getattr(database_update_obj, 'total_host_execution_duration', None)
                }
        
        # Handle case where data contains database_update object (common pattern)
        elif isinstance(data, dict) and 'database_update' in data:
            database_update = data['database_update']
            
            # Check if database_update is an object
            if hasattr(database_update, 'tables'):
                tables = getattr(database_update, 'tables', [])
            elif isinstance(database_update, dict):
                tables = database_update.get('tables', [])
            else:
                tables = []
            
            # Extract request_id from main data dict
            request_id = self._safe_extract(data, 'request_id')
            
            # Extract execution duration from main data dict
            execution_duration = self._safe_extract(data, 'total_host_execution_duration')
            
            return {
                'type': 'DatabaseUpdate',
                'tables': tables,
                'request_id': request_id,
                'execution_duration': execution_duration
            }
        
        # Original handling for dictionary format
        elif isinstance(data, dict):
            return {
                'type': 'DatabaseUpdate',
                'tables': [],
                'request_id': data.get('request_id'),
                'execution_duration': data.get('total_host_execution_duration')
            }
        
        # Fallback for unexpected data types
        else:
            logger.warning(f"Unexpected data type in _handle_database_update: {type(data)}")
            return {
                'type': 'DatabaseUpdate',
                'tables': [],
                'request_id': None,
                'execution_duration': None
            }

    def _handle_identity_token(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle identity token response"""
        # Handle case where data might be an IdentityToken object
        if hasattr(data, '__class__') and 'IdentityToken' in data.__class__.__name__:
            # data is an IdentityToken object directly
            return {
                'type': 'IdentityToken',
                'identity': getattr(data, 'identity', None),
                'token': getattr(data, 'token', None),
                'connection_id': getattr(data, 'connection_id', None)
            }
        elif isinstance(data, dict) and 'data' in data:
            # Handle wrapped object case
            token_obj = data.get('data')
            if hasattr(token_obj, 'identity'):
                return {
                    'type': 'IdentityToken',
                    'identity': getattr(token_obj, 'identity', None),
                    'token': getattr(token_obj, 'token', None),
                    'connection_id': getattr(token_obj, 'connection_id', None)
                }
        
        # Original dictionary handling
        elif isinstance(data, dict):
            return {
                'type': 'IdentityToken',
                'identity': data.get('identity'),
                'token': data.get('token'),
                'connection_id': data.get('connection_id')
            }
        
        # Fallback for unexpected data types
        else:
            logger.warning(f"Unexpected data type in _handle_identity_token: {type(data)}")
            return {
                'type': 'IdentityToken',
                'identity': None,
                'token': None,
                'connection_id': None
            }
    
    def _handle_unknown_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown message types."""
        logger.warning(f"Received unknown message type: {data}")
        
        # Handle objects by getting timestamp via getattr if needed
        timestamp = None
        if isinstance(data, dict):
            timestamp = data.get('timestamp')
        elif hasattr(data, 'timestamp'):
            timestamp = getattr(data, 'timestamp', None)
        
        return {
            'type': 'unknown',
            'raw_data': data,
            'timestamp': timestamp
        }
    
    def _extract_entities(self, table_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract entity data from table updates.
        
        Consolidates entity extraction logic from both projects.
        """
        entities = []
        
        try:
            # Handle different data structures
            if isinstance(table_data, list):
                for item in table_data:
                    entity = self._parse_entity_item(item)
                    if entity:
                        entities.append(entity)
            elif isinstance(table_data, dict):
                if 'rows' in table_data:
                    for row in table_data['rows']:
                        entity = self._parse_entity_item(row)
                        if entity:
                            entities.append(entity)
                else:
                    # Single entity
                    entity = self._parse_entity_item(table_data)
                    if entity:
                        entities.append(entity)
        
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
        
        return entities
    
    def _extract_players(self, table_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract player data from table updates."""
        players = []
        
        try:
            if isinstance(table_data, list):
                for item in table_data:
                    player = self._parse_player_item(item)
                    if player:
                        players.append(player)
            elif isinstance(table_data, dict):
                if 'rows' in table_data:
                    for row in table_data['rows']:
                        player = self._parse_player_item(row)
                        if player:
                            players.append(player)
                else:
                    player = self._parse_player_item(table_data)
                    if player:
                        players.append(player)
        
        except Exception as e:
            logger.error(f"Error extracting players: {e}")
        
        return players
    
    def _extract_circles(self, table_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract circle data from table updates."""
        circles = []
        
        try:
            if isinstance(table_data, list):
                for item in table_data:
                    circle = self._parse_circle_item(item)
                    if circle:
                        circles.append(circle)
            elif isinstance(table_data, dict):
                if 'rows' in table_data:
                    for row in table_data['rows']:
                        circle = self._parse_circle_item(row)
                        if circle:
                            circles.append(circle)
                else:
                    circle = self._parse_circle_item(table_data)
                    if circle:
                        circles.append(circle)
        
        except Exception as e:
            logger.error(f"Error extracting circles: {e}")
        
        return circles
    
    def _parse_entity_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse individual entity item."""
        try:
            # Common entity fields from both projects
            entity_data = {
                'entity_id': item.get('entity_id') or item.get('id'),
                'position': self._parse_position(item.get('position')),
                'mass': item.get('mass', 0.0),
                'radius': item.get('radius', 0.0),
                'velocity': self._parse_position(item.get('velocity')),
                'entity_type': item.get('entity_type', 'unknown')
            }
            
            # Only return if we have essential data
            if entity_data['entity_id'] is not None:
                return entity_data
                
        except Exception as e:
            logger.error(f"Error parsing entity item: {e}")
        
        return None
    
    def _parse_player_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse individual player item."""
        try:
            player_data = {
                'player_id': item.get('player_id') or item.get('id'),
                'name': item.get('name') or item.get('player_name'),
                'position': self._parse_position(item.get('position')),
                'direction': self._parse_position(item.get('direction')),
                'mass': item.get('mass', 0.0),
                'radius': item.get('radius', 0.0),
                'score': item.get('score', 0),
                'is_active': item.get('is_active', True)
            }
            
            if player_data['player_id'] is not None:
                return player_data
                
        except Exception as e:
            logger.error(f"Error parsing player item: {e}")
        
        return None
    
    def _parse_circle_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse individual circle item."""
        try:
            circle_data = {
                'circle_id': item.get('circle_id') or item.get('id'),
                'position': self._parse_position(item.get('position')),
                'radius': item.get('radius', 0.0),
                'color': item.get('color'),
                'circle_type': item.get('circle_type', 'unknown')
            }
            
            if circle_data['circle_id'] is not None:
                return circle_data
                
        except Exception as e:
            logger.error(f"Error parsing circle item: {e}")
        
        return None
    
    def _parse_position(self, position_data: Any) -> Optional[Dict[str, float]]:
        """Parse position data into consistent format."""
        if not position_data:
            return None
        
        try:
            if isinstance(position_data, dict):
                return {
                    'x': float(position_data.get('x', 0.0)),
                    'y': float(position_data.get('y', 0.0))
                }
            elif isinstance(position_data, (list, tuple)) and len(position_data) >= 2:
                return {
                    'x': float(position_data[0]),
                    'y': float(position_data[1])
                }
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing position data: {e}")
        
        return None
