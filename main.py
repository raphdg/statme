import os
import re
import sys
import time
import fnmatch
import datetime

from sys import stdout

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class EventHandler(FileSystemEventHandler):
    def __init__(self, path):
        super(EventHandler, self).__init__()
        self.start = datetime.datetime.now()
        self.path = path
        # My ignore file name is...
        self.gitignore_path = os.path.join(path, '.gitignore')

        # Lists of compiled RegExp objects
        self.include_regexps = []
        self.exclude_regexps = [re.compile('.*\.git.*')]

        # Update those lists
        if os.path.exists(self.gitignore_path):
            self._populate_gitignore_items()
        self.counter = 0.

    def on_modified(self, event):
        fullpath = event.src_path
        rel_path = os.path.relpath(fullpath, self.path)
        if not self.exclude(rel_path):
            self.counter += 1
            self.one_liner(self.counter)

    def one_liner(self, count):
        timedelta = datetime.datetime.now() - self.start
        minutes_elapsed = timedelta.seconds / 60.
        if minutes_elapsed >= 1:
            spm = count / minutes_elapsed
        else:
            spm = count

        stdout.write("\rAverage of %.1f saves per minute" % spm)
        stdout.flush()

    def exclude(self, rel_path):
        # First, check if the modified file is the gitignore file. If it's the
        # case, update include/exclude paths lists.
        if rel_path == self.gitignore_path:
            self._populate_gitignore_items()

        # Return True only if rel_path matches an exclude pattern AND does NOT
        # match an include pattern. Else, return False
        if (self._match_excl_regexp(rel_path) and
            not self._match_incl_regexp(rel_path)):
            return True

        return False

    def _populate_gitignore_items(self):
        '''This method populates include and exclude lists with compiled regexps
        objects.'''

        gitignore_items = self._parse_gitignore()
        if gitignore_items != None:
            # Let's compile them already :)
            self.include_regexps += [re.compile(x) for x in gitignore_items[0]]
            self.exclude_regexps += [re.compile(x) for x in gitignore_items[1]]

    def _match_excl_regexp(self, rel_path):
        '''Returns True if rel_path matches any item in exclude_regexp list.
        '''

        for regexp in self.exclude_regexps:
            if regexp.search(rel_path) is not None:
                return True

        return False

    def _match_incl_regexp(self, rel_path):
        '''Returns True if rel_path matches any item in include_regexp list.
        '''

        for neg_regexp in self.include_regexps:
            if neg_regexp.search(rel_path) is not None:
                return True

        return False

    def _parse_gitignore(self):
        """ Parses the .gitignore file in the repository.
        Returns a tuple with:
        1st elem: negative regexps (regexps to not match)
        2nd elem: regexps
        """
        lines = []  # contains each line of the .gitignore file
        results = []  # contains the result regexp patterns
        neg_results = []  # contains the result negative regexp patterns

        try:
            with open(self.gitignore_path, 'r') as f:
                lines = f.readlines()
        except IOError as err:
            raise Exception(format(err))

        # Sort the line in order to have inverse pattern first
        lines.sort(self._gitline_comparator)

        # For each git pattern, convert it to regexp pattern
        for line in lines:
            regexp = self._gitline_to_regexp(line)
            if regexp is not None:
                if not line.startswith('!'):
                    results.append(regexp)
                else:
                    neg_results.append(regexp)

        return neg_results, results

    def _gitline_comparator(self, a, b):
        """ Compares a and b. I want to have pattern started with '!'
        firstly
        """
        if a.startswith('!'):
            return -1
        elif b.startswith('!'):
            return 1
        else:
            return a == b

    def _gitline_to_regexp(self, line):
        """ Convert the unix pattern (line) to a regex pattern
        """
        negation = False  # if True, inverse the pattern

        # Remove the dirty characters like spaces at the beginning
        # or at the end, carriage returns, etc.
        line = line.strip()

        # A blank line matches no files, so it can serve as a
        # separator for readability.
        if line == '':
            return

        # A line starting with # serves as a comment.
        if line.startswith('#'):
            return

        # An optional prefix !  which negates the pattern; any
        # matching file excluded by a previous pattern will become
        # included again. If a negated pattern matches, this will
        # override
        if line.startswith('!'):
            line = line[1:]
            negation = True

        # If the pattern does not contain a slash /, git treats it
        # as a shell glob pattern and checks for a match against
        # the pathname relative to the location of the .gitignore
        # file (relative to the toplevel of the work tree if not
        # from a .gitignore file).

        # Otherwise, git treats the pattern as a shell glob
        # suitable for consumption by fnmatch(3) with the
        # FNM_PATHNAME flag: wildcards in the pattern will not
        # match a / in the pathname. For example,
        # "Documentation/*.html" matches "Documentation/git.html"
        # but not "Documentation/ppc/ppc.html" or
        # "tools/perf/Documentation/perf.html".
        regex = fnmatch.translate(line)
        regex = regex.replace('\\Z(?ms)', '')

        if not negation:
            regex = '.*%s.*' % regex

        return regex


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    event_handler = EventHandler(path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

