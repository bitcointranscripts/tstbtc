# Make executable with chmod +x <<filename.sh>>

echo "What is your github username?"
read USERNAME


# initialise the repo locally, add created file and commit
# git init -b main
git checkout -b ${2}
git add "$1" && git commit -m 'initial transcription using yt2btc script'

gh auth login

gh repo create --source=. --public

# add the remote github repo to local repo and push
git remote add yttbtc git@github.com:${USERNAME}/${2}.git
# git push --set-upstream origin master
git push -u yttbtc main
git remote add upstream https://github.com/bitcointranscripts/bitcointranscripts

echo "Done"
# echo "Done. Go to https://github.com/$USERNAME/$2 to see."