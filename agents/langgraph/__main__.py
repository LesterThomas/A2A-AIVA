from common.server import A2AServer
from common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from common.utils.push_notification_auth import PushNotificationSenderAuth
from agents.langgraph.task_manager import AgentTaskManager
from agents.langgraph.agent import AIVAAgent


import click
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=10000)
def main(host, port):
    """Starts the Currency Agent server."""
    print("--------------------------------")
    print("Starting Agent JSON-RPC server...")
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        skill = AgentSkill(
            id="tmforum_questions",
            name="TM Forum Questions and Answers",
            description="Answers questions on TM Forum Standards like Open-APIs, eTOM, SID, Functional Framework, etc.",
            tags=["Q&A", "Questions and Answers"],
            examples=[
                "What are the Open-APIs required to integrate partners into a Wholesale Broadband platform?",
                "Generate a server implementation for TMF673 Geographic Address Management API.",
            ],
        )
        agent_card = AgentCard(
            name="AIVA Agent",
            description="Answers questions and generates artefacts based on TM Forum Standards.",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=AIVAAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=AIVAAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(
                agent=AIVAAgent(), notification_sender_auth=notification_sender_auth
            ),
            host=host,
            port=port,
        )

        server.app.add_route(
            "/.well-known/jwks.json",
            notification_sender_auth.handle_jwks_endpoint,
            methods=["GET"],
        )

        logger.info(f"Starting server on {host}:{port}")
        server.start()
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
