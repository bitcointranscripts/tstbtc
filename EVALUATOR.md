# Productivity Notes for evaluation of Bitcoin Transcripts Reviews submissions

## Evaluating Submissions with Diffs

The script located at `scripts/check_diff.sh` fetches the original AI transcript
from the Queuer backend and applies it to the submission PR to facilitate the
evaluation process and compare changes efficiently.

Usage: `check_diff.sh <PR_number> <number_of_commits_in_the_PR>"`

After executing the command, an interactive rebase step takes place within you
local 'bitcointranscripts' repository. During this process, you must reposition
the "Temporary commit with added file" before the existing commits of the PR
and the initiate the rebase. For a visual demonstration of this rebase
procedure, refer to [this video demo](https://www.youtube.com/watch?v=HpLRIlpzn44).

Prerequisites
- bitcointranscripts: Set the `BITCOINTRANSCRIPTS_DIR` variable in your `.env`
file, pointing to the directory where the cloned [bitcointranscripts](https://github.com/bitcointranscripts/bitcointranscripts) repository is located.
- Backend connection: To establish a connection to the Queuer backend,
your `.env` file must contain a valid `QUEUE_ENDPOINT`.
- Authentication Token: Access to the Queuer API requires
authentication. Ensure your `.env` file includes a valid `BEARER_TOKEN` to
authenticate API requests.
