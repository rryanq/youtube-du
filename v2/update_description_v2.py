# Update the video description on several YouTube videos

import requests
import json
import pprint

import httplib2
import os
import sys

from googleapiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# specifies location of client secrets JSON object
CLIENT_SECRETS_FILE = "client_secrets_v2.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account.
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This is the string that will be appended to the end of all specified YouTube video descriptions
####################################
APPEND_STRING = """
\nTHIS IS A TEST
"""
####################################

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


def main():
    with open('video_ids.txt') as file:
        videos = json.load(file)

    # For testing, set videos to a list of two videos of mine that are very old and have less than 1000 views each
    videos = ['LHfYzVy-TKo', 'bb80xTDkDcA']

    # Initialize argparser arguments
    argparser.add_argument("--video-id", help="ID of video to update.", default="")
    argparser.add_argument("--tag", default="test_tag", help="Additional tag to add to video.")
    for video in videos:
        argparser.set_defaults(video_id=video)
        args = argparser.parse_args()
        youtube = get_authenticated_service(args)
        try:
            update_video(youtube, args)
        except HttpError as e:
            print("An HTTP error {} occurred:\n{}".format(e.resp.status, e.content))
        else:
            print("Description updated on video with video id '{}'.".format(args.video_id))


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

def update_video(youtube, options):
  # Call the API's videos.list method to retrieve the video resource.
  # print("video_id: ", options.video_id)
  videos_list_response = youtube.videos().list(
    id=options.video_id,
    part='snippet'
  ).execute()

  # If the response does not contain an array of "items" then the video was
  # not found.
  if not videos_list_response["items"]:
    print("Video '{}' was not found.".format(options.video_id))
    # sys.exit(1)

  # Since the request specified a video ID, the response only contains one
  # video resource. This code extracts the snippet from that resource.
  videos_list_snippet = videos_list_response["items"][0]["snippet"]

  # Preserve the descriptions already associated with the video. If the video does
  # not have a description, create a new one. Append the provided string to the
  # description associated with the video.
  if "description" not in videos_list_snippet:
      videos_list_snippet["description"] = ""
  videos_list_snippet["description"] += APPEND_STRING

  # Preserve any tags already associated with the video. If the video does
  # not have any tags, create a new array. Append the provided tag to the
  # list of tags associated with the video.
  if "tags" not in videos_list_snippet:
    videos_list_snippet["tags"] = []
  videos_list_snippet["tags"].append(options.tag)

  # Update the video resource by calling the videos.update() method.
  videos_update_response = youtube.videos().update(
    part='snippet',
    body=dict(
      snippet=videos_list_snippet,
      id=options.video_id
    )).execute()


if __name__ == "__main__":
    main()
