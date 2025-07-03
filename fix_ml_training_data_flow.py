#!/usr/bin/env python3
"""
Fix for ML training data flow issue.

The problem: ML training gets empty tables on initial connection because the
server returns current state (which is empty) before enter_game is called.

The solution: Wait for transaction updates after calling enter_game to get
the newly created game data.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from blackholio_client import GameClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLTrainingClient(GameClient):
    """Enhanced GameClient for ML training with proper data flow handling."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._game_data_received = asyncio.Event()
        self._transaction_data = None
        
        # Register for transaction updates to know when game data is ready
        self.on('TransactionUpdate', self._handle_transaction_update)
        self.on('transaction_update', self._handle_transaction_update)
    
    async def _handle_transaction_update(self, data: Dict[str, Any]) -> None:
        """Handle transaction updates to detect when game data is ready."""
        logger.info(f"🔄 Transaction update received: {data.get('type', 'unknown')}")
        
        # Store the transaction data
        self._transaction_data = data
        
        # Check if we now have game data
        if len(self.get_all_entities()) > 0:
            logger.info(f"✅ Game data received: {len(self.get_all_entities())} entities")
            self._game_data_received.set()
    
    async def enter_game_and_wait_for_data(self, player_name: str, timeout: float = 5.0) -> bool:
        """
        Enter game and wait for game data to be received.
        
        This is the key fix for ML training - it ensures we wait for the
        transaction update that contains the game data after enter_game.
        """
        logger.info(f"🎮 Entering game as {player_name}")
        
        # Clear the event
        self._game_data_received.clear()
        
        # Call enter_game
        success = await self.enter_game(player_name)
        if not success:
            logger.error("❌ Failed to call enter_game reducer")
            return False
        
        logger.info("⏳ Waiting for game data...")
        
        try:
            # Wait for game data with timeout
            await asyncio.wait_for(self._game_data_received.wait(), timeout=timeout)
            
            # Double-check we have data
            entities = self.get_all_entities()
            players = self.get_all_players()
            
            logger.info(f"✅ Game data ready: {len(players)} players, {len(entities)} entities")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout waiting for game data after {timeout}s")
            
            # Debug information
            logger.info(f"Current state: {len(self.get_all_players())} players, {len(self.get_all_entities())} entities")
            
            return False


async def test_ml_training_fix():
    """Test the ML training data flow fix."""
    
    # Create enhanced client
    client = MLTrainingClient("localhost:3000", "blackholio")
    
    logger.info("1. Connecting to server...")
    await client.connect()
    
    # Check initial data (should be empty)
    logger.info("2. Initial data check:")
    logger.info(f"   Players: {len(client.get_all_players())}")
    logger.info(f"   Entities: {len(client.get_all_entities())}")
    
    # Enter game and wait for data
    logger.info("3. Entering game and waiting for data...")
    success = await client.enter_game_and_wait_for_data("ML_Test_Player")
    
    if success:
        logger.info("4. ✅ Success! Game data received:")
        logger.info(f"   Players: {len(client.get_all_players())}")
        logger.info(f"   Entities: {len(client.get_all_entities())}")
        
        # Verify we can get player entities
        player_entities = []
        for entity in client.get_all_entities():
            # Check if this entity belongs to a player
            for player in client.get_all_players():
                if hasattr(entity, 'player_id') and entity.player_id == player.player_id:
                    player_entities.append(entity)
        
        logger.info(f"   Player entities: {len(player_entities)}")
    else:
        logger.error("4. ❌ Failed to receive game data")
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_ml_training_fix())