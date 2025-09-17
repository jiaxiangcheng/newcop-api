from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging
import signal
from discord_service import discord_service
from bot import discord_bot
from config import API_HOST, API_PORT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Discord Message Deletion API",
    description="API for deleting Discord messages based on order ID",
    version="1.0.0"
)

class DeleteMessageRequest(BaseModel):
    """Request model for delete-discord-message endpoint"""
    channel_id: int = Field(..., description="Discord channel ID where to search for messages")
    order_id: str = Field(..., description="Order ID to match in webhook messages")
    limit: Optional[int] = Field(100, description="Maximum number of messages to search (default: 100)")
    title: Optional[str] = Field(None, description="Product title to match if order_id doesn't match")
    variant: Optional[str] = Field(None, description="Size/variant to match if order_id doesn't match")

class DeleteMessageResponse(BaseModel):
    """Response model for delete-discord-message endpoint"""
    success: bool
    deleted_count: int
    messages_checked: Optional[int] = None
    deleted_messages: Optional[list] = None
    search_criteria: Optional[dict] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint"""
    try:
        # Simple health check without Discord dependency
        return {
            "message": "App is running",
            "status": "healthy",
            "service": "Discord Message Deletion API",
            "version": "1.0.0",
            "endpoints": {
                "POST /delete-discord-message": "Delete Discord messages matching order ID",
                "GET /health": "Health check endpoint"
            }
        }
    except Exception as e:
        logger.error(f"Error in root endpoint: {e}")
        return {
            "message": "App is running with warnings",
            "status": "degraded",
            "service": "Discord Message Deletion API",
            "version": "1.0.0",
            "error": str(e)
        }

@app.post("/delete-discord-message", response_model=DeleteMessageResponse)
async def delete_discord_message(request: DeleteMessageRequest):
    """
    Delete Discord messages that match the specified order ID, with fallback to title/variant matching

    This endpoint searches for webhook messages in a Discord channel that contain
    the specified order ID. If no order ID match is found and title/variant are provided,
    it will attempt to match messages based on embed title and size/variant fields.

    Args:
        request: DeleteMessageRequest containing order ID and optional title/variant

    Returns:
        DeleteMessageResponse with operation results
    """
    try:
        logger.info(f"Processing delete request for channel {request.channel_id}")
        logger.info(f"Search criteria - Order ID: {request.order_id}, Title: {request.title}, Variant: {request.variant}")

        # Call the Discord service to search and delete messages
        result = await discord_service.search_and_delete_messages(
            channel_id=request.channel_id,
            order_id=request.order_id,
            limit=request.limit,
            title=request.title,
            variant=request.variant
        )
        
        if result["success"]:
            logger.info(f"Successfully processed request. Deleted {result['deleted_count']} messages")
        else:
            logger.error(f"Request failed: {result.get('error', 'Unknown error')}")
        
        return DeleteMessageResponse(**result)
        
    except Exception as e:
        logger.error(f"Unexpected error in delete_discord_message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from discord_service import discord_service

    discord_status = "ready" if discord_service.is_ready() else "not_ready"

    return {
        "status": "healthy",
        "service": "discord-message-deletion-api",
        "discord_bot_status": discord_status
    }

async def run_servers():
    """Run both FastAPI server and Discord bot concurrently"""
    import uvicorn

    # Create uvicorn server
    config = uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="info")
    server = uvicorn.Server(config)

    logger.info(f"Starting Discord Message Deletion API on {API_HOST}:{API_PORT}")
    logger.info("Starting Discord bot with slash commands...")

    try:
        # Create tasks for both services
        api_task = asyncio.create_task(server.serve())
        bot_task = asyncio.create_task(discord_bot.start())

        # Wait for either task to complete or fail
        done, pending = await asyncio.wait(
            [api_task, bot_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # If one task completes, cancel the other
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Check if any task failed
        for task in done:
            if task.exception():
                logger.error(f"Task failed with exception: {task.exception()}")
                raise task.exception()

    except Exception as e:
        logger.error(f"Error in run_servers: {e}")
        # Graceful shutdown will be handled by signal handlers
        raise

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, _):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        # Create a new event loop for cleanup if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(shutdown_handler())
        except RuntimeError:
            pass

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

async def shutdown_handler():
    """Handle graceful shutdown"""
    logger.info("Starting graceful shutdown...")

    try:
        await discord_bot.stop()
    except Exception as e:
        logger.error(f"Error stopping Discord bot: {e}")

    logger.info("Shutdown complete")

if __name__ == "__main__":
    setup_signal_handlers()

    try:
        asyncio.run(run_servers())
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running servers: {e}")
        raise
    finally:
        logger.info("Application stopped")
