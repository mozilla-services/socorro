#!/usr/bin/env bash
# tag a new socorro release on locally and create a corresponding github release

# if this goes wrong and you need to delete a github release:
#    git tag -d $tag
#    git push $remote :$tag
#    open "https://github.com/mozilla/socorro/releases/"
# and delete the (now) draft

set -eo pipefail

cd $(dirname "$0")/..

dryRun=""
[[ $1 == "--dry-run" ]] && {
  dryRun="y"
  echo "dry run! commands will be echoed but not run"
}

(git branch | grep '* master') || {
  echo "only release from the master branch."
  exit 1
}

echo "fetching tags from github.com/mozilla/socorro"
git fetch -t git@github.com:mozilla/socorro.git

remote=$(git remote -v | grep "mozilla/socorro.git" | cut -f 1 | head -n 1 | tr -d ' ')
[ -z "$remote" ] && {
  echo "could not find your local mozilla/socorro remote alias, cannot continue"
  exit 1
}

lastTag=$(git tag | grep '^[0-9]*$' | tail -n 1)
tag=$(($lastTag + 1))

if [ ! -z "$dryRun" ]; then
    echo "    git tag \"$tag\" && git push $remote \"$tag\""
else
    git tag "$tag" && git push $remote "$tag"
fi

if [ -f ~/.config/hub ]; then
    echo "Hub detected! Using your hub token to create the release directly!"
    token=$(cut -d : -f 2 ~/.config/hub | grep "[0-9]" | tr -d ' ')

    if [ ! -z "$dryRun" ]; then
        echo "    curl -X POST -d "{ \"tag_name\": \"$tag\", \"name\": \"$tag\", \"body\": \"https://github.com/mozilla/socorro/compare/$lastTag...$tag\" }" -u $token:x-oauth-basic https://api.github.com/repos/mozilla/socorro/releases"
        echo "    open "https://github.com/mozilla/socorro/releases/$tag""
    else
        curl -sS -X POST -d "{ \"tag_name\": \"$tag\", \"name\": \"$tag\", \"body\": \"https://github.com/mozilla/socorro/compare/$lastTag...$tag\" }" -u $token:x-oauth-basic https://api.github.com/repos/mozilla/socorro/releases
        open "https://github.com/mozilla/socorro/releases/$tag"
    fi
    echo "tagging was successful!"
    exit 0
fi

printf "
Hub not detected! You're gonna have to fill out a form.

Tag $tag has been pushed and is waiting to be made into a proper release. In a
moment your browser will open to the new releases page. Input the following:

tag:
$tag

Release Title:
$tag

Describe this release:
https://github.com/mozilla/socorro/compare/$lastTag...$tag

"
open "https://github.com/mozilla/socorro/releases/new"
