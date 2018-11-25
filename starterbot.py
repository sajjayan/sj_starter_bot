import os
import time
import re
import phonenumbers
import uuid
from slackclient import SlackClient
from twilio.rest import Client

# instantiate Slack client & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
twilio_client = Client()
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# environment variables
BOT_ID = os.environ.get("BOT_ID")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
EXAMPLE_COMMAND = "do"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
AT_BOT = "<@"+BOT_ID+">"
print ("bot id is "+AT_BOT)
#AT_BOT = "<@UAU71BZDM>"
CALL_COMMAND = "call"
TWIMLET = "https://twimlets.com/echo?Twiml=%3CResponse%3E%0A%20%20%3CDial%3E%3CConference%3E{{name}}%3C%2FConference%3E%3C%2FDial%3E%0A%3C%2FResponse%3E&"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)
    # Finds and executes the given command, filling in response
    response = None
    response = "Not sure what you mean. Use the *" + CALL_COMMAND + "* command with numbers, delimited by spaces."
    print("Command is "+str(command))
    # This is where you start to implement more commands!
    if command.startswith(EXAMPLE_COMMAND):
        response = "Sure...write some more code then I can do that!"
    if command.startswith("hello"):
        response = "Hello, How  can I help you!!!"
    if command.startswith("Good Morning"):
        response = "Hello, Very Good Morning!!!"
    if command.startswith(CALL_COMMAND):
        response = call_command(command[len(CALL_COMMAND):].strip())
    # slack_client.api_call("chat.postMessage", channel=channel,
                          # text=response, as_user=True)
    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response, as_user=True
    )

def call_command(phone_numbers_list_as_string):
    """
        Validates a string of phone numbers, delimited by spaces, then
        dials everyone into a single call if they are all valid.
    """
    # generate random ID for this conference call
    conference_name = str(uuid.uuid4())
    # split phone numbers by spaces
    phone_numbers = phone_numbers_list_as_string.split(" ")
    # make sure at least 2 phone numbers are specified
    if len(phone_numbers) > 1:
        # check that phone numbers are in a valid format
        are_numbers_valid, response = validate_phone_numbers(phone_numbers)
        if are_numbers_valid:
            # all phone numbers are valid, so dial them together
            for phone_number in phone_numbers:
                twilio_client.calls.create(to=phone_number,
                                           from_=TWILIO_NUMBER,
                                           url=TWIMLET.replace('{{name}}',
                                           conference_name))
            response = "calling: " + phone_numbers_list_as_string
    else:
        response = "the *call* command requires at least 2 phone numbers"
    return response

def validate_phone_numbers(phone_numbers):
    """
        Uses the python-phonenumbers library to make sure each phone number
        is in a valid format.
    """
    invalid_response = " is not a valid phone number format. Please correct the number and retry. No calls have yetbeen dialed."
    for phone_number in phone_numbers:
        try:
            validate_phone_number = phonenumbers.parse(phone_number)
            if not phonenumbers.is_valid_number(validate_phone_number):
                return False, phone_number + invalid_response
        except:
            return False, phone_number + invalid_response
    return True, None

def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is a firehose of data, so
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip(),output['channel']
    return None, None

if __name__ == "__main__":
    # if slack_client.rtm_connect(with_team_state=False):
        # print("Starter Bot connected and running!")
        # # Read bot's user ID by calling Web API method `auth.test`
        # starterbot_id = slack_client.api_call("auth.test")["user_id"]
        # while True:
            # command, channel = parse_bot_commands(slack_client.rtm_read())
            # if command:
                # handle_command(command, channel)
            # time.sleep(RTM_READ_DELAY)
    # else:
        # print("Connection failed. Exception traceback printed above.")
    if slack_client.rtm_connect():
        print("CallBot connected and running!")
        while True:
            command, channel = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                handle_command(command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
