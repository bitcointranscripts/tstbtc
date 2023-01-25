# Make executable with chmod +x <<filename.sh>>

# check if github is logged in
if gh auth status;  then
  echo 'already logged into github'
else
  gh auth login
fi
 #check if the repo exists
if [ -d "./bitcointranscripts/" ]; then
  # set the repo to the current directory
  git pull upstream master
  cd bitcointranscripts || exit
else
  # fork and clone the repo
  gh repo fork bitcointranscripts/bitcointranscripts --clone
  gh repo set-default "${4}"/bitcointranscripts

  # set the repo to the current directory
  cd bitcointranscripts || exit
fi
# check if the current branch is master else checkout master
git_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$git_branch" != "master" ]; then
  git checkout master
fi

gh repo sync --branch master

# create a new branch or checkout the branch if it exists
if [ "$(git show-ref --quiet refs/heads/${5}${3})" ]; then
  git checkout "${5}${3}"
else
  git checkout -b "${5}${3}"
fi

# check if the loc exists or not
if [ ! -d "./${2}" ]; then
  mkdir -p "${2}"
fi

#discover the directories
IFS=/ read -ra dirs <<< "${2}"

# switch to the first directory
cd "${dirs[0]}" || return #tvpeter

# check if the index file exists
if [ ! -f ./_index.md ]; then
  echo -e "---\ntitle: ${dirs[0]}\n---\n\n{{< childpages >}}" >> _index.md
fi

# goto the second directory
cd "${dirs[1]}" || return #yt2btc

# check if the index file exists
if [ ! -f ./_index.md ]; then
  echo -e "---\ntitle: ${dirs[0]}\n---\n\n{{< childpages >}}" >> _index.md
fi

# goto the original directory
cd ../..

# move the transcript to the directory
mv "${1}" "./${2}"
