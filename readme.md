## Functionality
1. Converts stories on [https://www.fanfiction.net] to epub.
Go to fanfiction-server.herokuapp.com/fanfiction_epub/<fanfiction.net story id> to get the converted epub file.
ex. https://fanfiction-server.herokuapp.com/fanfiction_epub/11322704

# Setup

You'll need a `constants.py` file in the root of the project folder containing a variable for the
headers for the get request to get your account's fanfiction alerts.
ie.
```
headers = {"accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
"accept-encoding":"gzip, deflate, br",
"accept-language":"en-US,en;q=0.9",
"cache-control":"no-cache",
"cookie":"<COOKIE HERE>",
"pragma":"no-cache",
"referer":"https://www.fanfiction.net/account/settings.php",
"upgrade-insecure-requests": "1",
"user-agent": "Mozilla/5.0 (Macin
```
## Modifications that had to be made

In the EbookLib module in epub.py on line 908:
```
el.text = v[0]
```
was changed to
```
el.text = str(v[0])
```

## Other notes
Path where epubs are located in iBooks:
`~/Library/Mobile\ Documents/iCloud\~com\~apple\~iBooks/Documents`