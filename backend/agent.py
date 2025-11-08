import os
import sys
from openai import OpenAI
from slack import fetch_all_messages
from check_meetings import check_for_meetings
from parse_messages import parse_messages_list 
from dotenv import load_dotenv
load_dotenv()



"""Create and return an OpenAI client configured for the custom endpoint."""

key = os.environ.get('OPENAI_API_KEY') or os.environ.get('API_KEY')

# Resolve API key from param or environment (only needed for real requests)
if not key:
    raise RuntimeError('No OpenAI API key provided. Set OPENAI_API_KEY or API_KEY in the environment.')
client = OpenAI(

    api_key=key,
    base_url=os.environ.get('OPENAI_BASE_URL')
)
    

    # response = openai_client.chat.completions.create(
    #     model="gpt-4",
    #     messages=[
    #         {
    #             "role": "system",
    #             "content": "You are an assistant that extracts meeting information from Slack messages. Identify any meetings mentioned, including date, time, and participants."
    #         },
    #         {
    #             "role": "user",
    #             "content": f"Analyze these Slack messages and extract any meeting information:\n\n{messages_text}"
    #         }
    #     ],
    #     functions=[
    #         {
    #             "name": "extract_meeting",
    #             "description": "Extract meeting details from messages",
    #             "parameters": {
    #                 "type": "object",
    #                 "properties": {
    #                     "meeting_title": {"type": "string"},
    #                     "date": {"type": "string"},
    #                     "time": {"type": "string"},
    #                     "participants": {
    #                         "type": "array",
    #                         "items": {"type": "string"}
    #                     },
    #                     "location": {"type": "string"}
    #                 },
    #                 "required": ["meeting_title"]
    #             }
    #         }
    #     ],
    #     function_call="auto"
    # )

def master_agent():
    """Main agent that orchestrates the workflow."""

    channel_id = "C09RKGDKDRT"  # Replace with your channel ID
    
    print("Fetching Slack messages...")
    try:
        print(f'Fetching messages from Slack channel {channel_id}...', file=sys.stderr)
        messages = fetch_all_messages(channel_id)
        if not messages:
            print(f'Error: No messages fetched from Slack channel {channel_id}.', file=sys.stderr)
            sys.exit(2)
    except Exception as e:
        print(f'Error fetching from Slack: {e}', file=sys.stderr)
        sys.exit(2)

    
    parsed_messages = parse_messages_list(messages)
    
    if not parsed_messages:
        print("No new messages found.")
        return

    print(f"Analyzing {len(parsed_messages)} messages for meetings...")
    result = check_for_meetings(parsed_messages, client)

    # Check if function was called
    if result:
        print("Meeting found!")
        print(result)
    else:
        print("No meetings detected.")
        print(result)

if __name__ == "__main__":
    master_agent()