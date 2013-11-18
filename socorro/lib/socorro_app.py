import argparse
import logging
import os
import shutil
import socket
import subprocess
import sys

logger = logging.getLogger('socorro')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class Socorro(object):
    def __init__(self, superuser=None):
        self.superuser = superuser

    def cmd(self, cmd, background=False, cwd=None):
        logger.debug('Running command: %s' % cmd)
        if background:
            proc = subprocess.Popen(cmd, cwd=cwd)
            return proc
        else:
            proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            output = proc.communicate()
            logger.debug('output from %s: %s' % (cmd, output))
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, output)
            return output

    def copydist(self, config):
        if not os.path.exists('config/%s.ini' % config):
            logger.info('Copying default config file for %s' % config)
            shutil.copyfile('config/%s.ini-dist' % config,
                            'config/%s.ini' % config)

    def stackwalker(self, clean=False):
        logger.info('Building breakpad stackwalker')
        if clean:
            self.cmd(['make', 'clean'])
        self.cmd(['make', 'breakpad', 'stackwalker'])

    def checkPort(self, address, port):
        s = socket.socket()
        try:
            s.connect((address, port))
        except socket.error:
            return False
        return True

    def checkdb(self):
        if not self.checkPort('localhost', 5432):
            logger.error('PostgreSQL is not running, shutting down...')
            logger.error('HINT: is PostgreSQL running on localhost port 5432?')
            sys.exit(1)

        try:
            self.cmd(['psql', 'breakpad', '-c', 'SELECT 1'])
        except Exception:
            return False
        return True

    def setupdb(self, clean=False):
        logger.info('Setting up new DB')
        sql = "SELECT * from pg_user WHERE usename='%s' AND usesuper"
        try:
            self.cmd(['psql', 'template1', '-c', sql % self.superuser])
        except Exception:
            logger.error('ERROR: No postgres superuser named %s'
                         % self.superuser)
            logger.error('HINT: try creating a superuser account:')
            logger.error('sudo su - postgres')
            logger.error('createuser -s %s' % self.superuser)
            logger.error('psql -c "ALTER USER %s WITH ENCRYPTED PASSWORD '
                         '\'aPassword\'"' % self.superuser)
            sys.exit(1)

        self.copydist('alembic')

        logger.info('Generating synthetic test data ("fakedata")')
        setupdb_cmd = ['python', 'socorro/external/postgresql/setupdb_app.py',
                       '--database_name=breakpad', '--fakedata',
                       '--logging.stderr_error_logging_level=40',
                       '--database_superusername=%s' % self.superuser]
        if clean:
            setupdb_cmd.append('--dropdb')
            setupdb_cmd.append('--force')
        self.cmd(setupdb_cmd)
        self.cmd(['python', 'socorro/cron/crontabber.py',
                  '--job=weekly-reports-partitions', '--force'])

    def checkRabbit(self):
        return self.checkPort('localhost', 5672)

    def checkES(self):
        return self.checkPort('localhost', 9200)

    def run(self, virtualenv=None, ip_address=None):
        if ip_address is None:
            ip_address = 'localhost'

        for config in ['collector', 'processor', 'middleware']:
            self.copydist(config)

        if virtualenv:
            logger.debug('Using virtualenv: %s' % virtualenv)
            pybin = '%s/bin/python' % virtualenv
        else:
            pybin = 'python'

        # FIXME use IP
        logger.info('Running servers in dev mode')
        procs = []
        for app in ['collector', 'processor', 'middleware']:
            # FIXME logging is too noisy
            procs.append(self.cmd([pybin,
                                   'socorro/%s/%s_app.py' % (app, app),
                                   '--admin.conf=./config/%s.ini' % app,
                                   '--web_server.ip_address=%s' % ip_address,
                                   '--logging.stderr_error_logging_level=20'],
                                  background=True))

        logger.info('Running webapp-django in dev mode')
        django_config = 'webapp-django/crashstats/settings/local.py'
        if not os.path.exists(django_config):
            shutil.copyfile('%s-dist' % django_config, django_config)

        snippet = "MWARE_BASE_URL = 'http://%s:8883'" % ip_address

        with open(django_config, 'r+') as f:
            conf = f.read()

        with open(django_config, 'w') as f:
            for line in conf.split('\n'):
                if line.startswith('MWARE_BASE_URL') and \
                   line != snippet:
                    f.write('#' + line + '\n')
                    f.write(snippet + '\n')
                else:
                    f.write(line + '\n')

        procs.append(self.cmd([pybin, 'manage.py', 'runserver',
                              '%s:8000' % ip_address],
                              background=True, cwd='./webapp-django'))
        return procs


def main():
    parser = argparse.ArgumentParser(prog='socorro')
    subparsers = parser.add_subparsers(dest='subcommand')

    parser.add_argument('--virtualenv', help='path to virtualenv')

    parser_setup = subparsers.add_parser('setup', help='set up socorro')
    parser_setup.add_argument('-c', '--clean', action='store_true',
                              help='destroy and recreate environment')

    parser_run = subparsers.add_parser('run', help='run socorro')
    parser_run.add_argument('-i', '--ip_address')

    parser_submitter = subparsers.add_parser('submitter')
    parser_submitter.add_argument('-u', '--url', required=True)
    parser_submitter.add_argument('-s', '--search_root', required=True)

    args = parser.parse_args()

    socorro = Socorro(superuser=os.environ['USER'])
    if args.subcommand == 'setup':
        logger.info('Checking breakpad stackwalker')
        if not os.path.exists('stackwalk/bin/stackwalker') or args.clean:
            socorro.stackwalker(clean=args.clean)
        logger.info('Checking PostgreSQL')
        if not socorro.checkdb() or args.clean:
            socorro.setupdb(clean=args.clean)
        logger.info('Checking RabbitMQ')
        if not socorro.checkRabbit():
            logging.error('RabbitMQ not running, shutting down')
            sys.exit(1)
        logger.info('Checking ElasticSearch')
        if not socorro.checkES():
            logging.error('ElasticSearch not running, shutting down')
            sys.exit(1)

    if args.subcommand == 'run':
        procs = socorro.run(virtualenv=args.virtualenv,
                            ip_address=args.ip_address)
        while True:
            if None not in set([x.poll() for x in procs]):
                print 'All background processes stopped, shutting down'
                sys.exit(0)

    if args.subcommand == 'submitter':
        url = args.url
        search = args.search_root
        output = socorro.cmd(['python', 'socorro/collector/submitter_app.py',
                              '-u', url,
                              '--logging.stderr_error_logging_level=10',
                              '-s', search])
        for line in output[1].split('\n'):
            if 'submission response' in line:
                logger.info(line)
                sys.exit(0)
        logger.error('No submission response found, output: %s' % output[1])

if __name__ == '__main__':
    main()
