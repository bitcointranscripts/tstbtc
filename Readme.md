# YTB_TO_BTCSCRIPT

This project converts youtube videos to bitcoinscripts and opens a PR on [bitcoinscript](https://github.com/bitcointranscripts/bitcointranscripts) repo. It uses `youtube_transcript_api` to transcribe the videos, then collects meta data about the video using `requests_html`. It then uses the supplied cli arguments and file to open a Pull Request on the [bitcoinscript](https://github.com/bitcointranscripts/bitcointranscripts) repo.

## Steps:

The step-by-step flow for the scripts are:

- transcribe given video and generate the output file

- authenticate the user to github

- fork the transcript repo/use their existing fork, clone it and branch out

- copy the transcript file to the new transcript repo

- commit new file and push  

- then open a PR 

##  Usage

`python3 -m venv venv` creates a virtual environment

`source venv/bin/activate` activates the virtual environment

`python3 -m pip install -r requirements.txt` install all the libraries used in the application

To check the version:
`python -m yttbtc -v` view the application version

`python3 -m yttbtc yt2btc {video_id} {file_name}` create video transcript supplying the id of the youtube video and the source/year

## OTHER REQUIREMENTS

To enable us fork bitcointranscript repo and open a PR, we require you to login into your github account. Kindly install `GITHUB CLI` using the instructions on their repo [here](https://github.com/cli/cli#installation). Following the prompt, please select the below options from the prompt to login:

-  what account do you want to log into? `Github.com`

-  what is your preferred protocol for Git operations? `SSH`

-  Upload your SSH public key to your Github account? `skip`

-  How would you like to authenticate Github CLI? `Login with a web browser`

copy the generated one-time pass-code and paste in the browser to authenticate if you have enabled 2FA