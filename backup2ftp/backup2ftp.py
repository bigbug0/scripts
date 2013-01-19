#!/usr/bin/env python2
# coding: utf-8
# Copyright 2013, Valentin Novikov <lannor74@gmail.com>

import os
import glob
import tarfile as libTarfile
from hashlib import md5
from myftplib import MyFTPLib

class Backup2Ftp:

    def __init__(self, ftp_server, ftp_user, ftp_passw, debug=False):
        self._ftp_auth = (ftp_server, ftp_user, ftp_passw)
        self.ftp = MyFTPLib(debug=debug)

    def getsubdirs(self, path, level_depth=10):
        dirs_for_arch = []
        for iiter, (cpath, subdirs, files) in enumerate(os.walk(path)):
            if level_depth >= 0 and iiter >= level_depth or iiter > 1000 : break
            if len(files) > 0:
                dirs_for_arch.append([ cpath, cpath[len(path):].strip(os.path.sep) ])
        return dirs_for_arch

    def maketar(self, srcdir, cachedir, ex='*.*'):
        cachedir = os.path.join(cachedir, md5(srcdir).hexdigest())
        outtarfile = os.path.join(cachedir, os.path.basename(srcdir) + '.tar.gz')

        if not os.path.exists(cachedir):
            os.makedirs(cachedir)

        cwd = os.getcwd()
        os.chdir(srcdir)

        try:
            print(u'Creating tar: {!r} ...'.format(outtarfile))
            with libTarfile.open(outtarfile, 'w:gz') as tfp:
                for f in glob.glob(ex):
                    print(u'  Adding {!r} ...'.format(f))
                    tfp.add(f)
        except Exception as err:
            print(repr(err))
            return None
        else:
            return outtarfile
        finally:
            os.chdir(cwd)

    def upload2ftp(self, filename, ftpoutdir):
        if self.ftp.login(*self._ftp_auth):
            self.ftp.upload(filename, ftpoutdir, force=0)
            self.ftp.close()

if __name__ == '__main__':
    source_dir = '/tmp/test'
    cache_dir = '/tmp/cache'
    ftp_host = '127.0.0.1'
    ftp_user = ''
    ftp_passw = ''
    ex = '*.txt'

    try:
        b2f = Backup2Ftp(ftp_host, ftp_user, ftp_passw, debug=True)
        for (srcdir, ftpoutdir) in b2f.getsubdirs(source_dir):
            tarfile = b2f.maketar(srcdir, cachedir=cache_dir, ex=ex)
            if tarfile != None:
                b2f.upload2ftp(tarfile, ftpoutdir+'/')
                os.remove(tarfile)
    except Exception as err:
        print(repr(err))
    finally:
        if tarfile and os.path.exists(tarfile):
            os.remove(tarfile)