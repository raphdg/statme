# statme #
Gives some stats about your coding style. At the moment, it shows you how many
files you save per minute, with or without changes to it.

_statme_ will recursively monitor a folder excluding all files present in the `.gitignore` file as well as the `.git` folder
itself.

# Usage #
`python main.py <path>`

If _path_ is not provided, the current directory is watched.
