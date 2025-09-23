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

        # Check if Discord bot is ready, with extended retry logic for cold starts
        max_wait_time = 60  # Total maximum wait time in seconds (for Heroku cold starts)
        retry_delay = 3  # Initial retry delay
        max_retry_delay = 10  # Maximum retry delay
        total_waited = 0

        while not discord_service.is_ready() and total_waited < max_wait_time:
            # Log progress to help with debugging
            remaining_time = max_wait_time - total_waited
            logger.info(f"Discord bot not ready, waiting {retry_delay}s... (waited: {total_waited}s, remaining: {remaining_time}s)")

            await asyncio.sleep(retry_delay)
            total_waited += retry_delay

            # Gradually increase retry delay for efficiency (exponential backoff)
            retry_delay = min(retry_delay * 1.2, max_retry_delay)

        # Final check
        if not discord_service.is_ready():
            logger.error(f"Discord bot is not ready after {max_wait_time}s - this may be a Heroku cold start issue")
            raise HTTPException(
                status_code=503,
                detail=f"Discord bot is not ready after {max_wait_time}s. This may be due to a cold start. Please try again in 30-60 seconds."
            )

        logger.info("Discord bot is ready, processing request")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_discord_message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status for cold start monitoring"""
    from discord_service import discord_service
    import time

    discord_ready = discord_service.is_ready()
    discord_status = "ready" if discord_ready else "not_ready"

    # Determine overall service status
    if discord_ready:
        overall_status = "healthy"
        message = "Service fully operational"
    else:
        overall_status = "starting"
        message = "Discord bot initializing - API requests will wait for readiness"

    return {
        "status": overall_status,
        "message": message,
        "service": "discord-message-deletion-api",
        "discord_bot_status": discord_status,
        "timestamp": int(time.time()),
        "cold_start_info": {
            "note": "On Heroku cold starts, Discord bot may take 30-60s to initialize",
            "recommendation": "Wait for discord_bot_status: 'ready' before making API calls"
        }
    }

async def run_servers():
    """Run both FastAPI server and Discord bot concurrently"""
    import uvicorn

    # Create uvicorn server
    config = uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="info")
    server = uvicorn.Server(config)

    logger.info("Starting Discord bot with slash commands...")
    logger.info(f"Starting Discord Message Deletion API on {API_HOST}:{API_PORT}")

    try:
        # Start Discord bot first
        bot_task = asyncio.create_task(discord_bot.start())

        # Wait a moment for bot to initialize
        await asyncio.sleep(1)

        # Wait for bot to be ready before starting API server (with longer timeout for cold starts)
        max_wait = 45  # seconds - increased for Heroku cold starts
        wait_interval = 2  # seconds - slightly longer intervals
        waited = 0

        while not discord_service.is_ready() and waited < max_wait:
            logger.info(f"Waiting for Discord bot to be ready... ({waited}s/{max_wait}s)")
            await asyncio.sleep(wait_interval)
            waited += wait_interval

        if discord_service.is_ready():
            logger.info("Discord bot is ready! Starting API server...")
        else:
            logger.warning(f"Discord bot not ready after {max_wait}s, starting API server anyway (cold start scenario)")
            logger.warning("API requests will handle bot readiness checks with extended timeouts")

        # Start API server
        api_task = asyncio.create_task(server.serve())

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
