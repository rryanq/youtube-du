# YouTube Description Updater
These are the docs for the YouTube Description Updater, written by Ryan Quinlan.

## Setup
1. Install python3 if it hasn't already been installed
2. Create a virtual environment: `python3 -m venv env`
3. Activate the virtual environment: `source ./env/bin/activate`
4. Install the backend dependencies: `pip install -r requirements.txt`

## Project Structure
Inside of the application folder (currently v2), there are 6 important folders:
  1. update_description_v2.py: this is the main python script that is run
  2. client_secrets_v2.json: this file contains a JSON object that has all client ID and client secret info. This is necessary to authenticate oneself to YouTube. These are known as Oauth 2.0 credenitals and must be obtained here: https://console.developers.google.com/apis/credentials?project=meta-scanner-228205&folder&organizationId
  3. video_ids.txt: this file contains a list object of all of the IDs of every YouTube video I have. It is not currently being kept up to date, but could easily be automated if needed. I would just rather not run code to obtain them freshly all the time because I have an API limit from YouTube that I need to adhere to.
  4. update_description_v2.py-oauth2.json: this file is automatically generated on a correct run of the program
  5. run_tests: a bash script containing test runs of the program
  6. test_inputs/: a folder containing test inputs used in the run_tests script

## Running the Program
In order to run the program:
1. You must be signed into the google account of the YouTube channel you wish to modify.
2. The credentials specified in client_secrets_v2.json MUST be up to date. You can obtain new ones here if the first run returns 403 Forbidden: https://console.developers.google.com/apis/credentials?project=meta-scanner-228205&folder&organizationId
  - When you create the new credentials, you also need to specify this as the redirect URI: `http://localhost:8080/`
  - When new credentials are obtained, replace old ones in client_secrets_v2.json. `client_id` and `client_secret` both need to be replaced with new values.
3. The API key that is used when using the `--all` flag is restricted to specific IP addresses. Before running the program with this flag, you need to make sure that access is being provided to your IP address. If you don't, you will get the following error: "data = data['items'], KeyError: 'items'". Here is where you can modify the IP addresses that are allowed to use this program: https://console.cloud.google.com/apis/credentials/key/b3771649-540a-47ca-a9d6-e019e760fec2?orgonly=true&project=meta-scanner-228205&supportedpurview=organizationId
4. You must be in a correct virtual environment (`source ./env/bin/activate`) and be in the `v2` folder (`cd v2`)
5. Run the program:
    ```
    python3 update_description_v2.py --find <file containing string to find> --replace_with <file containing string to replace find string with> --video_ids <file containing list object of video_ids to operate on> --all (if specified, run find and replace on all YouTube videos)
    ```
If the program authenticates successfully, but it has been a while since it was run, the command line may display a link that needs to be copied and pasted into the browser to finish authentication. This link leads to a consent page that I had to set up. It is like an official app where you have to give the app permission to make changes to your YouTube channel. (see consent_screen.png). Be sure to sign into the correct gmail account which has access to the channel you wish to update. If it additionally gives you the option to sign into either a personal account or a brand account, be sure to select the correct one which needs to be modified. Once you say yes, then the program will run.
6. If you do not plan to provide a list of video ids to operate on and would instead like to operate on all video ids for a given channel, then you must also provide an `api_credentials.json` file that contains the following:
    ```
    {
      "API_KEY": <a valid youtube API key which can be obtained here: https://console.developers.google.com/apis/credentials?project=meta-scanner-228205>
      "CHANNEL_ID": <the channel ID of the channel that you are operating on. For example, the channel ID for Quin's Coins is: 'UC0Il3poeADV0QEio9GWPEHw'>
    }
    ```