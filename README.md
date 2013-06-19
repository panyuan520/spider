if windows:
     run the run.bat  
else:
    spider.py -u "http://www.sina.com.cn" -d 2 -f "spider.log" -l 2 --test=""  -t 10 --dbfile "spider.db" --key="HTML5" 

keys:  
    -u crawl url 
    -d deep 
    -f logpath  
    -l loglevel (1<= deep <=5)  
    --test doctest (parse_url, insert_db, run) 
    --dbfile database path  
    --crawl key 

if the key is null will use default.