import config
import logging
import pprint
import queue
import threading
import time
from apiexception import APIException
from slackclient import SlackClient

# Slack client API object
slack = {}

log = logging.getLogger(__name__)

# Ensures that the bot doesn't send more than one message per second
outgoingMessageQueue = queue.Queue()


# Taken from http://chriskiehl.com/article/parallelism-in-one-line/
class MessageQueueConsumer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            # Blocks until a message is available
            post_message = outgoingMessageQueue.get()
            try:
                post_message()
            except Exception as e:
                pass # Not sure what to do here other than log
            time.sleep(1)


def init():
    global slack
    slack = SlackClient(config.get()["slackToken"])
    sendMessageThread = MessageQueueConsumer()
    sendMessageThread.start()


# Performs an API call without raising errors
def unsafe_call(method, **kwargs):
    global slack
    log.info("Performing API call %s", method)
    return slack.api_call(method, **kwargs)


# Performs an API call
# Raises an APIException if the call fails
def call(method, **kwargs):
    result = unsafe_call(method, **kwargs)
    if result["ok"] != True:
        exception = APIException('"ok" was false: {0}'.format(pprint.format(result)))
        raise exception
    else:
        log.info("API call succeeded.")
        return result


def rtm_connect():
    return slack.rtm_connect()


def rtm_read():
    return slack.rtm_read()


def send_message(channelID, messageStr):
    if len(messageStr) > 4000:
        raise APIException("Attempted to send message over 4000 characters starting with: {0}".format(
            messageStr[:3000]
        ))

    def post_message():
        call("chat.postMessage",
             channel=channelID,
             text=messageStr,
             link_names=True,
             as_user=True)

    outgoingMessageQueue.put(post_message)


def send_code(channelID, messageStr, filetype="javascript", comment=None):
    def post_code():
        if not comment:
            call("files.upload",
                 content=messageStr,
                 filetype=filetype,
                 channels=channelID)
        else:
            call("files.upload",
                 content=messageStr,
                 filetype=filetype,
                 channels=channelID,
                 initial_comment=comment)

    outgoingMessageQueue.put(post_code)


def send_error(channelID, messageStr):
    send_code(channelID, messageStr, comment="@noppers")

def get_history(channelID, unixStampOldest, unixStampNewest = None):
    if (unixStampNewest is None):
        return call("channels.history",
                    channel=channelID,
                    count=1000,
                    inclusive=True,
                    oldest=unixStampOldest)
    else:
        return call("channels.history",
                    channel=channelID,
                    count=1000,
                    inclusive=True,
                    latest=unixStampNewest,
                    oldest=unixStampOldest)