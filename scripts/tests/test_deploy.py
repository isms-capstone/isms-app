"""Exercise deploy ordering/failure gates without touching Docker or a real server."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class DeployTests(unittest.TestCase):
    def execute(self, fail='', actual='approved', env_file=True):
        with tempfile.TemporaryDirectory(prefix='isms-deploy-qa-') as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            shutil.copyfile(Path(__file__).resolve().parents[1] / 'deploy.sh', root / 'scripts/deploy.sh')
            if env_file:
                (root / '.env.staging').write_text('QA_ONLY=true\n')
            tools = root / 'bin'
            tools.mkdir()
            for name, body in {
                'git': '#!/bin/sh\nprintf "%s\\n" "$QA_COMMIT"\n',
                'docker': '#!/bin/sh\nprintf "%s\\n" "$*" >> "$QA_LOG"\n'
                          'if [ -n "$QA_FAIL" ]; then case "$*" in *"$QA_FAIL"*) exit 42;; esac; fi\n',
            }.items():
                target = tools / name
                target.write_text(body, newline='\n')
                target.chmod(0o755)
            log = root / 'calls.log'
            environment = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'],
                               QA_COMMIT=actual, QA_LOG=log.as_posix(), QA_FAIL=fail)
            if os.name == 'nt':
                startup = root / 'bash-env'
                startup.write_text('export PATH="$(cygpath -u "$QA_TOOLS"):$PATH"\n', newline='\n')
                environment.update(BASH_ENV=startup.as_posix(), QA_TOOLS=tools.as_posix())
            result = subprocess.run([os.environ.get('TEST_BASH', 'bash'),
                                     (root / 'scripts/deploy.sh').as_posix(), 'staging', 'approved'],
                                    env=environment, capture_output=True, text=True)
            return result, log.read_text().splitlines() if log.exists() else []

    def test_migration_and_preflight_precede_application_replacement(self):
        result, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 6)
        for call, expected in zip(calls, ['config --quiet', 'build app', 'up -d --wait',
                                         'app.db.migration_state', 'alembic upgrade head',
                                         'up -d --no-deps --wait']):
            self.assertIn(expected, call)
        self.assertTrue(all('--env-file .env.staging -p isms-staging' in call for call in calls))

    def test_failed_preflight_or_migration_never_replaces_app(self):
        for failure in ('app.db.migration_state', 'alembic upgrade head'):
            result, calls = self.execute(fail=failure)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(any('up -d --no-deps' in call for call in calls))

    def test_wrong_commit_or_missing_environment_never_calls_docker(self):
        for options in ({'actual': 'unapproved'}, {'env_file': False}):
            result, calls = self.execute(**options)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
