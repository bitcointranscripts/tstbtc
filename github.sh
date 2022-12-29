# Make executable with chmod +x <<filename.sh>>

echo "What is your github username?"
read USERNAME


# initialise the repo locally, add created file and commit
git init
git add "$1"
git commit -m 'initial commit - initial transcription using yt2btc script'
git remote add upstream https://github.com/bitcointranscripts/bitcointranscripts



#  use github API to log the user in
curl -u ${USERNAME} https://api.github.com/${USERNAME}/repos -d "{\"name\": \"${2}\"}"

# add the remote github repo to local repo and push
git remote add origin https://github.com/${USERNAME}/${2}.git
# git push --set-upstream origin master


echo "Done. Go to https://github.com/$USERNAME/$2 to see."