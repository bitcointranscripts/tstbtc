# YTB_TO_BTCSCRIPT

This project converts youtube videos to bitcoinscripts and opens a PR. It uses youwhisper to transcribe the videos, then collects meta data about the video using command-line arguments. It then uses that information to open a Pull Request on the bitcoinscript repo.

##  Usage

`python3 -m venv venv` creates a virtual environment

`source venv/bin/activate` activates the virtual environment

`python3 -m pip install -r requirements.txt` install all the libraries used in the application

To check the version:
`python -m yttbtc -v` view the application version

`python3 -m yttbtc yt2btc {video_id} {file_name}` create video transcript supplying the id of the youtube video and the source/year

## OTHER REQUIREMENTS

To enable us create a new repo to push the transcribed file and open a PR, install `GITHUB CLI` using the instruction [here](https://github.com/cli/cli#installation). Following the prompt, please select the below options from the prompt to login:

-  what account do you want to log into? `Github.com`

-  what is your preferred protocol for Git operations? `SSH`

-  Upload your SSH public key to your Github account? `skip`

-  How would you like to authenticate Github CLI? `Login with a web browser`

copy the generated one-time pass-code and paste in the browser to authenticate