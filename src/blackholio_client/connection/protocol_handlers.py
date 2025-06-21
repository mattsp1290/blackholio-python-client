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
            'SubscriptionUpdate': self._handle_subscription_update,
            'Error': self._handle_error,
            'Connected': self._handle_connected,
            'Disconnected': self._handle_disconnected,
        }
        
        logger.debug(f"Initialized {self.protocol_version} protocol handler")
    
    def process_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process v1.1.2 protocol message.
        
        Consolidates message processing logic from both existing implementations.
        """
        try:
            # Determine message type
            message_type = self._get_message_type(data)
            
            if not message_type:
                logger.warning(f"Unknown message type in data: {data}")
                return None
            
            # Process with appropriate handler
            if message_type in self.message_handlers:
                return self.message_handlers[message_type](data)
            else:
                logger.warning(f"No handler for message type: {message_type}")
                return self._handle_unknown_message(data)
                
        except Exception as e:
            logger.error(f"Error processing v1.1.2 message: {e}")
            logger.debug(f"Problematic message data: {data}")
            return None
    
    def format_outgoing_message(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format outgoing message for v1.1.2 protocol."""
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        base_message = {
            'protocol': 'v1.json.spacetimedb',
            'timestamp': timestamp,
            'type': message_type
        }
        
        # Add message-specific data
        base_message.update(data)
        
        return base_message
    
    def _get_message_type(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract message type from incoming data."""
        # Try different possible message type fields
        type_fields = ['type', 'message_type', 'event', 'kind']
        
        for field in type_fields:
            if field in data:
                return data[field]
        
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
            subscription_data = data.get('subscription_update', data)
            
            return {
                'type': 'subscription_update',
                'status': subscription_data.get('status', 'unknown'),
                'tables': subscription_data.get('tables', []),
                'timestamp': data.get('timestamp')
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
        error_data = data.get('error', data)
        
        return {
            'type': 'error',
            'message': error_data.get('message', 'Unknown error'),
            'code': error_data.get('code'),
            'details': error_data.get('details'),
            'timestamp': data.get('timestamp')
        }
    
    def _handle_connected(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connection confirmation messages."""
        return {
            'type': 'connected',
            'status': data.get('status', 'connected'),
            'timestamp': data.get('timestamp')
        }
    
    def _handle_disconnected(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disconnection messages."""
        return {
            'type': 'disconnected',
            'reason': data.get('reason', 'Unknown'),
            'timestamp': data.get('timestamp')
        }
    
    def _handle_unknown_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown message types."""
        logger.warning(f"Received unknown message type: {data}")
        
        return {
            'type': 'unknown',
            'raw_data': data,
            'timestamp': data.get('timestamp')
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
