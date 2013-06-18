#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import gzip
import getopt
import logging
import sqlite3
import chardet
import socket
import doctest
import datetime
import StringIO
from Queue import Queue
from threading import Thread
from BeautifulSoup import BeautifulSoup
from urllib2 import Request, urlopen, URLError, HTTPError

reload(sys)
sys.setdefaultencoding("utf-8")

q = Queue()

#thread
class Worker(Thread):
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()
    
    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            try: func(*args, **kargs)
            except Exception, e: print e
            self.tasks.task_done()
            
#threadpool
class ThreadPool(object):
    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads): Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        self.tasks.join()


class Spider(object):
    
    def __init__(self):
        self.base = 'http://www.sina.com.cn'
        self.dbfile = 'spider.db'
        self.key = 'HTML5'
        self.thread = 10
        self.loglevel = 1
        self.logpath = 'spider.log'
        self.deep = 2
        self.maxdeep = 1
        self.logger = logging.getLogger()
        
    def set_url(self, url):
        self.base = url
        q.put(url)
    
    def set_log(self, path):
        self.logpath = path
        
    def set_loglevel(self, loglevel):
        if loglevel.isdigit() and 1<=int(loglevel)<=5:
            self.loglevel = loglevel
        else:
            print "loglevel error"
            sys.exit()
        
    def set_dbfile(self, path):
        self.dbfile = path
        
    def set_key(self, key):
        self.key = key
    
    def set_thread(self, thread):
        self.thread = thread
    
    def get_thread(self):
        return self.thread
    
    def set_deep(self, deep):
        if deep.isdigit():
            self.deep = int(deep)
        else:
            print "deep error"
            sys.exit()
    
    def parse_deep(self):
        return self.deep >= self.maxdeep
        
    #create log and database 
    def create_log(self):
        hdlr = logging.FileHandler(self.logpath)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.NOTSET)
    
    def create_db(self):
        try:
            connect = sqlite3.connect(self.dbfile)
            cursor = connect.cursor()
            try:
                cursor.execute("create table if not exists item(id INTEGER PRIMARY KEY, url CHAR(50))")
                connect.commit()
            except sqlite3.Error, e:
                self.logger("create table error, An error occurred:%s", e.args[0])
            except Exception as e:
                self.logger("create table error, %s " % e.args[0])
            finally:
                connect.close()
        except Exception as e:
            self.logger("connect db error, %s " % e.args[0])
            
    def create_opt(self):
        self.create_log()
        self.create_db()
        
    def parse_url(self, link):
        """
        >>> s.parse_url('http://www.sina.com.cn/1223.shtml')
        1
        """
        if self.base:
            domain = self.base
            if domain.startswith('http://'):
                domain = domain[7:]
            if domain.startswith('www.'):
                domain = domain[4:]
            if "/" in domain:
                domain = domain[0:domain.find('/')]
        ext = link.split(".")[-1]
        if ext in ['jpg', 'png', 'jped', 'swf']:
            return
        else:
            if link.find(domain) > -1:
                return True
    
    def insert_db(self, url):
        """
        >>> s.insert_db('http://www.sina.com.cn/123232.stml')
        True
        """
        try:
            connect = sqlite3.connect(self.dbfile, check_same_thread = False)
            cursor = connect.cursor()
            #inert or ignore the unique data
            cursor.execute("insert or ignore into item (url) values (?)", (url, ))
            connect.commit()
            return True
        except sqlite3.IntegrityError:
            self.logger.error("can't add %s" % url)
        except Exception as e:
            self.logger.error(e.args[0])
        finally:
            connect.close()
        
    def run(self, url):
        """
        >>> s.run('http://www.sina.com.cn')
        True
        """
        req = Request(url,
              headers = {"Referer": self.base,
                "User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)"
            })
        #check download url timeout
        html = None
        try:
            response = urlopen(url=req, timeout=30)
            headers = response.info()
            html = response.read()
            #if html is gzip
            if ('Content-Encoding' in headers and headers['Content-Encoding']) or \
                    ('content-encoding' in headers and headers['content-encoding']):
                data = StringIO.StringIO(html)
                gz = gzip.GzipFile(fileobj=data)
                html = gz.read()
                gz.close()
        except URLError, e:
            self.logger.error("The url %s can't open, URLError" % url)
        except HTTPError, e:
            self.logger.error("The url %s can't open, HTTPError" % url)
        except socket.timeout, e:
            self.logger.error("The url %s can't open, HTTPError" % url)
        except Exception as e:
            self.logger.error(e.args[0])
        if html:
            #check decode
            encoding = chardet.detect(html)['encoding']
            try:
                soup = BeautifulSoup(html.decode(encoding, 'ignore'))
                links = soup.findAll('a', href=True)
                keys = soup.findAll(text = re.compile(self.key))
                if len(keys) > 0:
                    self.insert_db(url)
                if len(links) > 0:
                    self.maxdeep += 1
                for link in links:
                    href = link['href']
                    if self.parse_url(href) and self.parse_deep():
                        q.put(href)
                return True
            except Exception as e:
                self.logger.error(e.args[0])
                
                
if __name__ == '__main__':

    #parse the argv to dict
    try:
        opts, args = getopt.getopt(sys.argv[1:], "u:d:f:l:t:", ["test=", "dbfile=", "key="])
        opts = dict(opts)
    except getopt.GetoptError:
        print "GetoptError, please check you argv"
        sys.exit()
        
    #test the module
    mud = opts.get('--test')
    if mud:
        if hasattr(Spider, mud):
            doctest.testmod(name=getattr(Spider, mud), extraglobs={'s':Spider()})
        else:
            print "The %s is't the Spider module" % mud
            sys.exit()
    else:
        doctest.testmod(extraglobs={'s':Spider()})
    
    spider = Spider()
    #iter get the args's key, value and check the value
    for k, v in opts.iteritems():
        if not v: continue
        if k == '-u':
            spider.set_url(v)
        elif k == '-d':
            spider.set_deep(v)
        elif k == '-f':
            spider.set_log(v)
        elif k == '-l':
            spider.set_loglevel(v)
        elif k == '-thread':
            spider.set_thread(v)
        elif k == '--dbfile':
            spider.set_dbfile(v)
        elif k == 'key':
            spider.set_key(v)   
            
    spider.create_opt()
    pool = ThreadPool(spider.get_thread())
    num = 0
    now = datetime.datetime.now()
    while True:
        url = q.get()
        end = datetime.datetime.now()
        if (end - now).seconds >= 10:
            print "download %s urls, all %s" % (num, q.qsize())
            now = end
        pool.add_task(spider.run, url)
        num += 1
        q.task_done()
    q.join()
    pool.wait_completion()
    
            
            
            
        