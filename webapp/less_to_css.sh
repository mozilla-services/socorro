# Convert LESS files to CSS, recursively within a directory.
# Requires `less` package to be installed (which it currently is for this repository) https://lesscss.org/usage/
# Before running, navigate to the desired directory to operate on.  
# Alternatively, you may add a directory path as an argument, e.g. `npm run convert:less ./crashstats`

if [ -z "$1" ]
then
  $1 = "."
fi
echo "converting LESS files in folder $1 to CSS"

for lessfile in $(find $1 -name "*.less"); do 
cssfile=$(echo $lessfile | sed 's/\.less$/.css/i')
echo "converted $lessfile";
rm -f $cssfile;
lessc --global-var="root-path='$PWD/crashstats/crashstats/static/crashstats/css'" $lessfile > $cssfile;
done;