from optparse import make_option
import os
import time
from subprocess import call, PIPE

from django.conf import settings
from django.core.management.base import BaseCommand

import git


path = lambda *a: os.path.join(settings.MEDIA_ROOT, *a)


class Command(BaseCommand):  # pragma: no cover
    help = ("Compresses css and js assets defined in settings.MINIFY_BUNDLES")
    option_list = BaseCommand.option_list + (
        make_option('-u', '--update-only', action='store_true',
                    dest='do_update_only', help='Updates the hash only'),
    )
    requires_model_validation = False
    do_update_only = False

    def update_hashes(self, update=False):
        def gitid(path):
            id = (git.repo.Repo(os.path.join(settings.ROOT, path))
                     .log('-1')[0].id_abbrev)
            if update:
                # Adds a time based hash on to the build id.
                return '%s-%s' % (id, hex(int(time.time()))[2:])
            return id

        build_id_file = os.path.realpath(os.path.join(settings.ROOT,
                                                      'build.py'))
        with open(build_id_file, 'w') as f:
            f.write('BUILD_ID_CSS = "%s"' % gitid('media/css'))
            f.write("\n")
            f.write('BUILD_ID_JS = "%s"' % gitid('media/js'))
            f.write("\n")
            f.write('BUILD_ID_IMG = "%s"' % gitid('media/img'))
            f.write("\n")

    def handle(self, **options):
        if options.get('do_update_only', False):
            self.update_hashes(update=True)
            return

        jar_path = (os.path.dirname(__file__), '..', '..', 'bin',
                'yuicompressor-2.4.4.jar')
        path_to_jar = os.path.realpath(os.path.join(*jar_path))

        v = ''
        if 'verbosity' in options and options['verbosity'] == '2':
            v = '-v'

        for ftype, bundle in settings.MINIFY_BUNDLES.iteritems():
            for name, files in bundle.iteritems():
                # Compile LESS files
                files_all = []
                for fn in files:
                    if fn.endswith('.less'):
                        fp = path(fn.lstrip('/'))
                        call('%s %s %s.css' % (settings.LESS_BIN, fp, fp),
                             shell=True)
                        # Outputs a *.less.css file.
                        files_all.append('%s.css' % fn)
                    else:
                        files_all.append(fn)

                concatted_file = path(ftype, '%s-all.%s' % (name, ftype,))
                compressed_file = path(ftype, '%s-min.%s' % (name, ftype,))
                real_files = [path(f.lstrip('/')) for f in files_all]

                # Concats the files.
                call("cat %s > %s" % (' '.join(real_files), concatted_file),
                     shell=True)

                # Compresses the concatenation.
                call("%s -jar %s %s %s -o %s" % (settings.JAVA_BIN,
                     path_to_jar, v, concatted_file, compressed_file),
                     shell=True, stdout=PIPE)

        self.update_hashes()
