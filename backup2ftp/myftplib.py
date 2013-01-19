# coding: utf-8
# Copyright 2013, Valentin Novikov <lannor74@gmail.com>

import os
import sys
import ftplib

from collections import namedtuple
from datetime import datetime

_DIR = namedtuple('DIR', 'filename, size, stamp, perm, user')
_FILE = namedtuple('FILE', 'filename, size, stamp, perm, user')

class MyFTPLib(object):

    def __init__(self, debug=False, *args, **kwargs):
        self._debug = debug
        self._ftp_conn = None

    def __del__(self):
        if self._ftp_conn:
            self._ftp_conn.close()
        del self._ftp_conn

    def close(self):
        self._ftp_conn.close()

    def debug(self, msg):
        if not self._debug: return
        if isinstance(msg, (set, list, tuple)):
            s = u''
            for m in msg:
                s += u' ' + unicode(m)
            msg = s
        print(u"DEBUG: {}: {}".format(datetime.now().strftime('%Y.%m.%d %H:%M:%S,%f'), msg))

    def _split_path(self, p, sep=None):
        if not sep: sep = os.path.sep
        return filter(lambda n: len(n) > 0, p.split(sep))

    def login(self, host, user=None, passw=None):
        if not user: user = 'anonymous'
        self._ftp_conn = ftplib.FTP(host)
        try:
            self.debug(u"Connecting to ftp://{}@{}...".format(user, host))
            if user and passw:
                self._ftp_conn.login(user, passw)
            else:
                self._ftp_conn.login()
        except ftplib.error_perm as err:
            self.debug(['login():', err])
            return False
        else:
            self.debug(['login():', 'OK'])
            return True

    def getfilesize(self, file):
        dirname = os.path.dirname(file)
        if not self.exists(dirname):
            return -1

        files = []
        basename = os.path.basename(file)

        self._ftp_conn.cwd(dirname)
        self._ftp_conn.retrlines('LIST', files.append)

        for f in files:
            perm, _, user, pid, size, month_name, day, time, name = f.split()
            if not perm.startswith('d') and name == basename:
                return int(size)
        return -1

    def listdir(self, to_list=False, ignore_empty_files=False):
        files = []
        result = [] if to_list else {'dirs':[], 'files':[]}
        self._ftp_conn.retrlines('LIST', files.append)

        for f in files:
            perm, _, user, pid, size, month_name, day, time, name = f.split()
            size = int(size)
            stamp = datetime.strptime("{} {} {}".format(month_name, day, time), '%b %d %H:%M')

            if perm.startswith('d'):
                obj, root = _DIR, 'dirs'
            else:
                obj, root = _FILE, 'files'
                if ignore_empty_files and size < 1:
                    continue

            if to_list:
                result.append(name)
            else:
                result[root].append(obj(name, size, stamp, perm, user))
        return result

    def exists(self, path):
        root_pwd = self._ftp_conn.pwd()
        try:
            for p in self._split_path(path):
                self._ftp_conn.cwd(p)
        except Exception as err:
            self.debug(['exists():', err])
            return False
        else:
            return True
        finally:
            self._ftp_conn.cwd(root_pwd)

    def exists_file(self, path):
        dirname = os.path.dirname(path)
        if not self.exists(dirname):
            return False
        self._ftp_conn.cwd(dirname)
        return os.path.basename(path) in self.listdir(to_list=True)

    def makedirs(self, path):
        root_pwd = self._ftp_conn.pwd()
        try:
            for d in self._split_path(path, '/'):
                if not self.exists(d):
                    self.debug(['makedirs():', 'Creating directory {0!r} in {1!r}'.format(d, path)])
                    self._ftp_conn.mkd(d)
                self._ftp_conn.cwd(d)
        except Exception as err:
            self.debug(['makedirs():', err])
            return False
        else:
            return True
        finally:
            self._ftp_conn.cwd(root_pwd)

    def upload(self, infile, outfile=None, force=0):
        """ @force:
                0 - не заменять файл
                1 - заменять всегда
                2 - заменить, если размер меньше существующего
                3 - заменить, если размер больше
        """

        if not os.path.exists(infile):
            return False

        if not outfile:
            outfile = infile

            if sys.platform.startswith('win') and infile[1] == ':':
                outfile = infile[2:].strip('\\')

        if outfile.endswith('/'):
            outfile = os.path.join(outfile, os.path.basename(infile))

        outfile = outfile.replace('\\', '/')
        outdir = os.path.dirname(outfile)
        outfilename = os.path.basename(outfile)

        infilesize = os.path.getsize(infile)
        outfilesize = self.getfilesize(outfile)
        if outfilesize >= 0:

            if force == 0:
                self.debug(['upload():', 'File is exists, skipped: {!r}'.format(outfile)])
                return True
            elif force == 2 and infilesize > outfilesize:
                self.debug(['upload():', 'Replace ignored ({} > {}): {!r}'.format(infilesize, outfilesize, outfile)])
                return True
            elif force == 3 and infilesize < outfilesize:
                self.debug(['upload():', 'Replace ignored ({} < {}): {!r}'.format(infilesize, outfilesize, outfile)])
                return True

        try:
            self.makedirs(outdir)
            self.debug(['upload():', 'Change directory: {!r}'.format(outdir)])
            self._ftp_conn.cwd(outdir)
            self.debug(['upload():', 'Uploading file ({:,}Mb): {!r} ...'.format(infilesize/1048576, outfilename)])
            self._ftp_conn.storbinary('STOR {}'.format(outfilename), open(infile, 'rb'), 8196)
        except Exception as err:
            self.debug(['upload():', err])
            return False
        else:
            self.debug(['upload():', 'OK'])
            return True

#if __name__ == '__main__':
#    f = MyFTPLib(debug=True)
#    f.login('192.168.81.128', 'valya', '12345')
#    f.upload('D:\\test.txt', '/root/', force=3)