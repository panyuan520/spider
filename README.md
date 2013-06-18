if windows run the run.bat  <br />
else spider.py -u "http://www.sina.com.cn" -d 2 -f "spider.log" -l 2 --test=""  -t 10 --dbfile "spider.db" --key="HTML5"  <br />

keys:  <br />
    -u crawl url <br />
	-d deep <br />
	-f logpath  <br />
	-l loglevel (1<= deep <=5)  <br />
	--test doctest (parse_url, insert_db, run) <br />
	--dbfile database path  <br />
	--crawl key <br />
<br />
if the key is null will use default.