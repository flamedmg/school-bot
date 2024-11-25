import logging
from src.events.broker import broker, app

logger = logging.getLogger(__name__)

class EventManager:
    """Manages event system lifecycle."""
    
    async def start(self):
        """Start the event system."""
        logger.info("Starting event system")
        
        # Connect to broker
        await broker.connect()
        
        # Start the stream app
        await app.start()
        logger.info("Event system started successfully")

    async def stop(self):
        """Stop the event system."""
        logger.info("Stopping event system")
        if app:
            await app.stop()
        if broker:
            await broker.close()
        logger.info("Event system stopped successfully")

# Global instance
event_manager = EventManager()
