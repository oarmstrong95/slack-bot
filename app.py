# Import necessary libraries
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain_openai.chat_models import ChatOpenAI
from helper import process_conversation_history, update_chat
import logging

# Define the logger object
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('env')

# Get Slack bot token, Slack app token, and OpenAI API key from environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Initialize the Slack Bolt app and OpenAI API
app = App(token=SLACK_BOT_TOKEN)

# Define a function to get the history of a conversation
def get_conversation_history(channel_id, thread_ts):
    """
    Retrieves the conversation history for a given channel and thread.

    Args:
        channel_id (str): The ID of the channel.
        thread_ts (str): The timestamp of the thread.

    Returns:
        dict: The conversation history.

    """
    return app.client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        inclusive=True
    )

# Define the event handler for the app_mention event
@app.event("app_mention")
def command_handler(body, context):
    """
    Handle the command received from Slack.

    Args:
        body (dict): The request body containing the event details.
        context (dict): The context containing the bot user ID.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the execution.

    Comments:
        - The function extracts the channel ID, thread timestamp, and bot user ID from the request body.
        - It posts a waiting message to the Slack channel.
        - Retrieves the conversation history for the channel and thread.
        - Processes the conversation history to obtain a list of messages.
        - Calculates the number of tokens in the messages.
        - Initializes the ChatAPI with the OpenAI API key.
        - Sends the messages to the ChatAPI for completion.
        - Concatenates the response chunks and updates the chat if necessary.
        - Handles the stop condition if encountered.
        - Handles exceptions by posting an error message to the Slack channel.
    """

    # Set up logger
    logging.basicConfig(filename='log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        # Extract the channel ID, thread timestamp, and bot user ID from the request body
        channel_id = body['event']['channel']
        thread_ts = body['event'].get('thread_ts', body['event']['ts'])
        bot_user_id = context['bot_user_id']
        
        # Post a waiting message to the Slack channel
        slack_resp = app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Got your request. Please wait."
        )

        # Retrieve the conversation history for the channel and thread
        reply_message_ts = slack_resp['message']['ts']
        conversation_history = get_conversation_history(channel_id, thread_ts)
        messages = process_conversation_history(conversation_history, bot_user_id)
        logger.info(messages)

        # Intialize the ChatAPI with the OpenAI API key
        llm = ChatOpenAI(api_key=OPENAI_API_KEY)

        # Make the request to the ChatAPI for completion
        response = llm.invoke(messages)

        # Update the chat with the response
        update_chat(app, channel_id, reply_message_ts, response.content)
    
    except Exception as e:
        print(f"Error: {e}")
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"I can't provide a response. Encountered an error:\n`\n{e}\n`")


if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
