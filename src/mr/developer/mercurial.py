from mr.developer import common
import os
import subprocess

logger = common.logger

class MercurialError(common.WCError):
    pass

class MercurialWorkingCopy(common.BaseWorkingCopy):

    def __init__(self, source):
        if 'branch' not in source:
            source['branch'] = 'default'
        super(MercurialWorkingCopy, self).__init__(source)

    def hg_clone(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']
        branch = self.source['branch']
        
        if os.path.exists(path):
            self.output((logger.info, 'Skipped cloning of existing package %r.' % name))
            return
        self.output((logger.info, 'Cloned %r with mercurial.' % name))
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'clone', '--update', branch, '--quiet', '--noninteractive', url, path],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise MercurialError(
                'hg clone for %r failed.\n%s' % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def hg_pull(self, **kwargs):
        # NOTE: we don't include the branch here as we just want to update
        # to the head of whatever branch the developer is working on
        name = self.source['name']
        path = self.source['path']
        self.output((logger.info, 'Updated %r with mercurial.' % name))
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(['hg', 'pull', '-u'], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise MercurialError(
                'hg pull for %r failed.\n%s' % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            if update:
                self.update(**kwargs)
            elif self.matches():
                self.output((logger.info, 'Skipped checkout of existing package %r.' % name))
            else:
                raise MercurialError(
                    'Source URL for existing package %r differs. '
                    'Expected %r.' % (name, self.source['url']))
        else:
            return self.hg_clone(**kwargs)

    def matches(self):
        name = self.source['name']
        path = self.source['path']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'showconfig', 'paths.default'], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise MercurialError(
                'hg showconfig for %r failed.\n%s' % (name, stderr))
        # now check that the working branch is the same
        return (self.source['url'] + '\n' == stdout)

    def status(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'status'], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        status = stdout and 'dirty' or 'clean'
        if kwargs.get('verbose', False):
            return status, stdout
        else:
            return status

    def update(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        if not self.matches():
            raise MercurialError(
                "Can't update package %r because its URL doesn't match." %
                name)
        if self.status() != 'clean' and not kwargs.get('force', False):
            raise MercurialError(
                "Can't update package %r because it's dirty." % name)
        return self.hg_pull(**kwargs)

common.workingcopytypes['hg'] = MercurialWorkingCopy
