import re
from trafilatura import extract, fetch_url
from trafilatura.settings import use_config

newconfig = use_config()
newconfig.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

# Define the system prompt message
SYSTEM_PROMPT = '''
You are an AI assistant. 
You will answer the question as truthfully as possible.
If you're unsure of the answer, say Sorry, I don't know.
'''

def extract_url_list(text):
    """
    Extracts a list of URLs from the given text.

    Args:
        text (str): The text to search for URLs.

    Returns:
        list or None: A list of URLs found in the text, or None if no URLs are found.
    """
    url_pattern = re.compile(
        r'<(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)>'
    )
    url_list = url_pattern.findall(text)
    return url_list if len(url_list)>0 else None


def augment_user_message(user_message, url_list):
    """
    Augments the user message by replacing URLs with their extracted content.

    Args:
        user_message (str): The original user message.
        url_list (list): A list of URLs to extract content from.

    Returns:
        str: The augmented user message with extracted content appended.

    """
    all_url_content = ''
    for url in url_list:
        downloaded = fetch_url(url)
        url_content = extract(downloaded, config=newconfig)
        user_message = user_message.replace(f'<{url}>', '')
        all_url_content = all_url_content + f' Contents of {url} : \n """ {url_content} """'
    user_message = user_message + "\n" + all_url_content
    return user_message

def process_conversation_history(conversation_history, bot_user_id):
    """
    Process the conversation history and return a list of messages.

    Args:
        conversation_history (dict): The conversation history containing messages.
        bot_user_id (str): The ID of the bot user.

    Returns:
        list: A list of tuples representing messages. Each tuple contains the role (either "assistant" or "user") and the message text.

    """
    messages = []
    messages.append(("system", SYSTEM_PROMPT))
    # Iterate over each message in the conversation history, except the last one
    for message in conversation_history['messages'][:-1]:
        # Determine the role of the message (either "assistant" or "user")
        role = "assistant" if message['user'] == bot_user_id else "user"
        
        # Process the message and get the cleaned message text
        message_text = process_message(message, bot_user_id)
        
        # If the message text is not None, add it to the list of messages
        if message_text:
            messages.append((role, message_text))
    return messages

def process_message(message, bot_user_id):
    """
    Process the given message and return the processed message text.

    Args:
        message (dict): The message object containing the text and user information.
        bot_user_id (str): The ID of the bot user.

    Returns:
        str: The processed message text.

    Raises:
        None

    """
    message_text = message['text']
    role = "assistant" if message['user'] == bot_user_id else "user"
    if role == "user":
        url_list = extract_url_list(message_text)
        if url_list:
            message_text = augment_user_message(message_text, url_list)
    message_text = clean_message_text(message_text, role, bot_user_id)
    return message_text


def clean_message_text(message_text, role, bot_user_id):
    """
    Cleans the message text by removing the bot user mention and leading/trailing whitespace.

    Args:
        message_text (str): The original message text.
        role (str): The role of the user sending the message.
        bot_user_id (str): The ID of the bot user.

    Returns:
        str or None: The cleaned message text if the bot user mention is present or the role is "assistant", 
        otherwise None.
    """
    if (f'<@{bot_user_id}>' in message_text) or (role == "assistant"):
        message_text = message_text.replace(f'<@{bot_user_id}>', '').strip()
        return message_text
    return None


def update_chat(app, channel_id, reply_message_ts, response_text):
    """
    Update a chat message in Slack.

    Args:
        app (SlackApp): The Slack app instance.
        channel_id (str): The ID of the channel where the message is located.
        reply_message_ts (str): The timestamp of the message to be updated.
        response_text (str): The updated text for the message.

    Returns:
        None
    """
    app.client.chat_update(
        channel=channel_id,
        ts=reply_message_ts,
        text=response_text
    )

