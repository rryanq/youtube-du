# Update the video description on several YouTube videos

import requests
import json
import pprint

import httplib2
import os
import sys
import click

from googleapiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# specifies location of client secrets JSON object
CLIENT_SECRETS_FILE = "client_secrets_v2.json"
# This is a way to access an API key and hardcoded channel ID for the purpose
# of obtaining a  list of all video ids for a given channel
API_CREDENTIALS_FILE = "api_credentials.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account.
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the {{ Cloud Console }}
{{ https://cloud.google.com/console }}

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

# define Python user-defined exceptions
class Error(Exception):
   """Base class for other exceptions."""
   pass

class StringNotFoundError(Error):
   """Raised when the string is not found."""
   pass

@click.command()
@click.option('--video_ids', required=False, type=str, help="File containing the list of video IDs of all YouTube videos to operate on.")
@click.option('--find', required=True, type=str, help="File containing the string that you would like to find in your YouTube descriptions.")
@click.option('--replace_with', required=True, type=str, help="File containing the string that you would like to replace the find string with.")
def main(video_ids, find, replace_with):

    # Initialize argparser arguments
    argparser.add_argument("--video_ids", default=video_ids)
    argparser.add_argument("--video_id", help="ID of video to update.", default="")
    argparser.add_argument("--find", default=find)
    argparser.add_argument("--replace_with", default=replace_with)

    # If video_ids file provided, extract list of video IDs from provided file
    if video_ids:
        with open(video_ids) as file:
            video_ids = json.load(file)
    # Otherwise, default is to find and replace on all videos
    # Get list of all video ids using an API key
    else:
        with open(API_CREDENTIALS_FILE) as file:
            data = json.load(file)
            api_key = data["API_KEY"]
            channel_id = data["CHANNEL_ID"]
        video_ids = get_video_ids(api_key, channel_id)

    # Update each video specified in the video_ids list
    for video_id in video_ids:
        argparser.set_defaults(video_id=video_id)
        args = argparser.parse_args()
        youtube = get_authenticated_service(args)
        try:
            update_video(youtube, args)
        except HttpError as e:
            print("An HTTP error {} occurred:\n{}".format(e.resp.status, e.content))
        except StringNotFoundError as e:
            info = e.args[0]
            print(info["message"])
        else:
            print("Description updated on video with video ID: '{}'.".format(args.video_id))


def get_authenticated_service(args):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
        scope=YOUTUBE_READ_WRITE_SCOPE,
        message=MISSING_CLIENT_SECRETS_MESSAGE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))


def get_video_ids(key, channelId):
    """Get video IDs for all videos on a given channel."""
    pageToken = ''
    moreResults = True
    videoIDs = []
    while(moreResults):
        url = 'https://www.googleapis.com/youtube/v3/search?key={}&channelId={}&part={}&maxResults={}&pageToken={}'.format(key, channelId, 'snippet', '50', pageToken)
        response = requests.get(url)
        data = response.json()
        if 'nextPageToken' in data:
            pageToken = data['nextPageToken']
        else:
            moreResults = False
            pageToken = ''
        data = data['items']
        for video in data:
            if 'videoId' in video['id'] and 'publishedAt' in video['snippet']:
                videoId = (video['id']['videoId'], video['snippet']['publishedAt'])
                videoIDs.append(videoId)
    # sort videoIDs in reverse chronological order based on date published
    videoIDs.sort(key=lambda x: x[1], reverse=True)
    # remove publish date from list and return
    videoIDs = [videoID[0] for videoID in videoIDs]
    return videoIDs

def update_video(youtube, options):
    # Call the API's videos.list method to retrieve the video resource.
    videos_list_response = youtube.videos().list(
        id=options.video_id,
        part='snippet'
    ).execute()

    # If the response does not contain an array of "items" then the video was
    # not found.
    if not videos_list_response["items"]:
        print("Video '{}' was not found.".format(options.video_id))

    # Since the request specified a video ID, the response only contains one
    # video resource. This code extracts the snippet from that resource.
    videos_list_snippet = videos_list_response["items"][0]["snippet"]

    with open(options.find) as file:
        find_string = file.read()
    with open(options.replace_with) as file:
        replace_with_string = file.read()

    # remove trailing whitespace
    find_string = find_string.rstrip()
    replace_with_string = replace_with_string.rstrip()

    # Preserve the descriptions already associated with the video. If the video does
    # not have a description, create a new one. Update the description
    if "description" not in videos_list_snippet:
        videos_list_snippet["description"] = ""
    original_description = videos_list_snippet["description"]
    new_description = original_description
    if find_string in original_description:
        new_description = original_description.replace(find_string, replace_with_string)
    else:
        raise StringNotFoundError({"message": "replace string not found in description of video with ID: '{}'".format(options.video_id)})
    videos_list_snippet["description"] = new_description

    # Update the video resource by calling the videos.update() method.
    videos_update_response = youtube.videos().update(
        part='snippet',
        body=dict(
            snippet=videos_list_snippet,
            id=options.video_id
        )).execute()


if __name__ == "__main__":
    main()
