## Modifications that had to be made

In the EbookLib module in epub.py on line 908:
```
el.text = v[0]
```
was changed to
```
el.text = str(v[0])
```