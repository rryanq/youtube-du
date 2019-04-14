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


@click.command()
@click.option('--video_ids', required=True, type=str, help="File containing the list of video IDs of all YouTube videos to operate on.")
@click.option('--find', required=True, type=str, help="File containing the string that you would like to find in your YouTube descriptions.")
@click.option('--replace_with', required=True, type=str, help="File containing the string that you would like to replace the find string with.")
def main(video_ids, find, replace_with):

    # extract list of video IDs from provided file
    with open(video_ids) as file:
        video_ids = json.load(file)

    # Initialize argparser arguments
    argparser.add_argument("--video_ids", default=video_ids)
    argparser.add_argument("--video-id", help="ID of video to update.", default="")
    argparser.add_argument("--find", default=find)
    argparser.add_argument("--replace_with", default=replace_with)

    # Update each video specified in the video_ids list
    for video_id in video_ids:
        argparser.set_defaults(video_id=video_id)
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

    with open(options.find) as file:
        find_string = file.read()
    with open(options.replace_with) as file:
        replace_with_string = file.read()
    # get rid of newline at end of file
    find_string = find_string[0:-1]
    replace_with_string = replace_with_string[0:-1]

    # Preserve the descriptions already associated with the video. If the video does
    # not have a description, create a new one. Update the description
    if "description" not in videos_list_snippet:
        videos_list_snippet["description"] = ""
    original_description = videos_list_snippet["description"]
    new_description = original_description.replace(find_string, replace_with_string)
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
