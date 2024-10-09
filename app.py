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
load_dotenv()

# Get Slack bot token, Slack app token, and OpenAI API key from environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Initialize the Slack Bolt app and OpenAI API
app = App(token=SLACK_BOT_TOKEN)

def get_conversation_history(channel_id, thread_ts):
    return app.client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        inclusive=True
    )

def handle_message(body, say):
    try:
        event = body['event']
        channel_id = event['channel']
        thread_ts = event.get('thread_ts', event['ts'])
        user = event.get('user')

        # Ignore messages from bots or the app itself
        if 'bot_id' in event or user == app.client.auth_test()["user_id"]:
            return

        conversation_history = get_conversation_history(channel_id, thread_ts)
        messages = process_conversation_history(conversation_history, app.client.auth_test()["user_id"])
        
        logger.info(f"Processed messages: {messages}")

        slack_resp = say(text="Got your request. Please wait.", thread_ts=thread_ts)
        reply_message_ts = slack_resp['ts']

        llm = ChatOpenAI(api_key=OPENAI_API_KEY)
        response = llm.invoke(messages)

        update_chat(app, channel_id, reply_message_ts, response.content)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        say(text=f"I can't provide a response. Encountered an error:\n`\n{e}\n`", thread_ts=thread_ts)

@app.event("app_mention")
def app_mention_handler(body, say):
    handle_message(body, say)

@app.event("message")
def message_handler(body, say):
    event = body['event']
    # Only respond to messages in threads
    if 'thread_ts' in event:
        handle_message(body, say)

if __name__ == "__main__":
    # Set up logger
    logging.basicConfig(filename='log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()