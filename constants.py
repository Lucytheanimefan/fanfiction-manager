import os

headers = {"accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
"accept-encoding":"gzip, deflate, br",
"accept-language":"en-US,en;q=0.9",
"cache-control":"no-cache",
"cookie": os.environ.get("COOKIE", ""),
"pragma":"no-cache",
"referer":"https://www.fanfiction.net/account/settings.php",
"upgrade-insecure-requests": "1",
"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"}