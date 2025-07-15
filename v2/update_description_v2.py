# Update the video description on several YouTube videos

import re
import requests
import json
import pprint
from datetime import datetime

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


class StringNotFoundError(Error):
   """Raised when the string is not found."""


class IsYouTubeShortError(Exception):
    """Exception class for YouTube Shorts."""


class VideoTooOldError(Exception):
    """Exception class for YouTube videos that are too old."""


@click.command()
@click.option('--video_ids', required=False, type=str, help="File containing the list of video IDs of all YouTube videos to operate on.")
@click.option('--all', is_flag=True, default=False, help="Use this option to perform operations on all YouTube video descriptions")
@click.option('--find', required=False, type=str, help="File containing the string that you would like to find in your YouTube descriptions.")
@click.option('--replace_with', required=False, type=str, help="File containing the string that you would like to replace the find string with.")
@click.option('--append', required=False, type=str, help="File containing the string that you would like to append to the end of YouTube descriptions.")
def main(video_ids, find, replace_with, append, all):

    # Initialize argparser arguments
    argparser.add_argument("--all", action='store_const', const=all)
    argparser.add_argument("--video_ids", default=video_ids)
    argparser.add_argument("--find", default=find)
    argparser.add_argument("--replace_with", default=replace_with)
    argparser.add_argument("--append", default=append)
    argparser.add_argument("--video_id", help="ID of video to update.", default="")
    # Assign video_ids argument
    # If video_ids file provided, extract list of video IDs from provided file
    if video_ids and not all:
        with open(video_ids) as file:
            video_ids = json.load(file)
    # If 'all' option supplied, find and replace on all videos
    # Get list of all video ids using an API key
    elif all and not video_ids:
        with open(API_CREDENTIALS_FILE) as file:
            data = json.load(file)
            api_key = data["API_KEY"]
            channel_id = data["CHANNEL_ID"]
        video_ids = get_video_ids(api_key, channel_id)
    # otherwise, there is an error.
    else:
        print("Error: must supply either 'video_ids' option or provide '--all' flag")
        exit(1)

    # Determine operation to perform
    if find and replace_with and not append:
        # perform a find and replace
        for video_id in video_ids:
            argparser.set_defaults(video_id=video_id)
            args = argparser.parse_args()
            youtube = get_authenticated_service(args)
            try:
                find_and_replace_single_video(youtube, args)
            except HttpError as e:
                print("An HTTP error {} occurred:\n{}".format(e.resp.status, e.content))
            except StringNotFoundError as e:
                info = e.args[0]
                print(info["message"])
            except IsYouTubeShortError as e:
                print(f"Video '{args.video_id}' appears to be a YouTube Short, skipping...")
            except VideoTooOldError as e:
                print(f"Video '{args.video_id}' is too old and does not use the modern description format, skipping...")
            else:
                print("Description updated on video with video ID: '{}'.".format(args.video_id))
    elif append and not find and not replace_with:
        # perform append
        for video_id in video_ids:
            argparser.set_defaults(video_id=video_id)
            args = argparser.parse_args()
            youtube = get_authenticated_service(args)
            try:
                append_single_video(youtube, args)
            except HttpError as e:
                print("An HTTP error {} occurred:\n{}".format(e.resp.status, e.content))
            except StringNotFoundError as e:
                info = e.args[0]
                print(info["message"])
            else:
                print("Description updated on video with video ID: '{}'.".format(args.video_id))
    else:
        # invalid command line argument combination
        print("Error: Usage. Please use '--help' flag for more information")
        exit(1)


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
        # raise Exception(data)
        data = data['items']
        for video in data:
            if 'videoId' in video['id'] and 'publishedAt' in video['snippet']:
                videoId = (video['id']['videoId'], video['snippet']['publishedAt'])
                videoIDs.append(videoId)
    # remove duplicates
    videoIDs = [*set(videoIDs)]
    # sort videoIDs in reverse chronological order based on date published
    videoIDs.sort(key=lambda x: x[1], reverse=True)
    # remove publish date from list and return
    videoIDs = [videoID[0] for videoID in videoIDs]
    return videoIDs


def is_youtube_short(video_item):
    """Return true if the video is a YouTube Short, false otherwise."""
    if "contentDetails" in video_item and "duration" in video_item["contentDetails"]:
        duration_str = video_item["contentDetails"]["duration"]

        # Parse ISO 8601 duration string (e.g., "PT1M30S", "PT45S")
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if match:
            hours_str, minutes_str, seconds_str = match.groups()
            hours = int(hours_str) if hours_str else 0
            minutes = int(minutes_str) if minutes_str else 0
            seconds = int(seconds_str) if seconds_str else 0

            total_seconds = (hours * 3600) + (minutes * 60) + seconds

            # YouTube Shorts are generally 180 seconds or less
            return total_seconds <= 180
    return False


def uses_modern_description_format(video_item):
    """
    Checks if a video's published date is newer than January 7th, 2018.
    """
    TARGET_DATE_STR = "2018-01-07T00:00:00Z" # January 7th, 2018, 00:00:00 UTC
    TARGET_DATE = datetime.fromisoformat(TARGET_DATE_STR.replace('Z', '+00:00'))

    if "snippet" in video_item and "publishedAt" in video_item["snippet"]:
        published_at_str = video_item["snippet"]["publishedAt"]

        # Parse the publishedAt string into a datetime object.
        # The 'Z' indicates UTC, so we should convert it to a timezone-aware datetime.
        # Python 3.7+ fromisoformat handles 'Z' directly. For older versions,
        # you might need to use .replace('Z', '+00:00') or a library like dateutil.
        try:
            published_date = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
        except ValueError:
            # Handle cases where publishedAt might not be perfectly ISO 8601,
            # though it usually is for YouTube API.
            print(f"Warning: Could not parse publishedAt: {published_at_str}")
            return True

        # Compare the two datetime objects
        return published_date > TARGET_DATE
    return False


def find_and_replace_single_video(youtube, options):
    """Perform find and replace on the description of a single YouTube video."""
    # Call the API's videos.list method to retrieve the video resource.
    videos_list_response = youtube.videos().list(
        id=options.video_id,
        part='snippet,contentDetails'
    ).execute()

    # If the response does not contain an array of "items" then the video was
    # not found.
    if not videos_list_response["items"]:
        print("Video '{}' was not found.".format(options.video_id))

    # Since the request specified a video ID, the response only contains one
    # video resource. This code extracts the snippet from that resource.
    video_from_list = videos_list_response["items"][0]
    videos_list_snippet = video_from_list["snippet"]

    if is_youtube_short(video_from_list):
        raise IsYouTubeShortError()
    if not uses_modern_description_format(video_from_list):
        raise VideoTooOldError()

    with open(options.find) as file:
        find_string = file.read()
    with open(options.replace_with) as file:
        replace_with_string = file.read()

    # remove trailing whitespace
    find_string = find_string.rstrip()
    if len(find_string) < 4:
        print("Error: find string too short. A short find string could result in unintended consequences!")
        exit(1)
    replace_with_string = replace_with_string.rstrip()
    if len(replace_with_string) < 4:
        print("Error: replace_with string too short. A short replace_with string could result in unintended consequences!")
        exit(1)

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


def append_single_video(youtube, options):
    """Perform append operation on the description of a single YouTube video."""
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

    with open(options.append) as file:
        append_string = file.read()

    # remove trailing whitespace
    append_string = append_string.rstrip()

    # Preserve the descriptions already associated with the video. If the video does
    # not have a description, create a new one. Update the description
    if "description" not in videos_list_snippet:
        videos_list_snippet["description"] = ""
    original_description = videos_list_snippet["description"]
    new_description = original_description + append_string
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
