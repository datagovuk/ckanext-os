import os

from ckan.tests import BaseCase
from ckanext.os.testtools.mock_os_server import MOCK_OS_SERVER_HOST_AND_PORT

class MockOsServerCase(BaseCase):
    @classmethod
    def setup_class(self):
        self.pid = self._start_server()
        self._wait_for_url()

    @classmethod
    def teardown_class(self):
        self._stop_server(self.pid)

    @staticmethod
    def _start_server():
        import subprocess
        process = subprocess.Popen(['paster', '--plugin=ckanext-os', 'mock_os_server', 'run'])
        return process

    @staticmethod
    def _wait_for_url(url='http://%s/' % MOCK_OS_SERVER_HOST_AND_PORT, timeout=15):
        for i in range(int(timeout)*100):
            import urllib2
            import time
            try:
                response = urllib2.urlopen(url)
            except urllib2.URLError:
                time.sleep(0.1)
            else:
                break

    @staticmethod
    def _stop_server(process):
        pid = process.pid
        pid = int(pid)
        if os.system("kill -9 %d" % pid):
            raise Exception, "Can't kill foreign Mock OS Server (pid: %d)." % pid
