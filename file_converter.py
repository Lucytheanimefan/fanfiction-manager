from fanfiction_net_api import *
from ebooklib import epub
from os import path, remove
import os

iBOOKS_PATH = "~/Downloads/"


class Converter:

    def __init__(self, story_id):
        self.story_id = story_id
        self.fanfic = Story(story_id)

    def convert_to_epub(self):
        self.fanfic.download_data()
        self.fanfic.get_chapters()

        book = epub.EpubBook()

        print(self.fanfic.title)
        # set metadata
        book.set_identifier(str(self.story_id))
        book.set_title(self.fanfic.title)
        book.set_language('en')

        book.add_author(self.fanfic.author_id)

        intro_ch = epub.EpubHtml(title="Introduction", file_name='intro.xhtml')
        # intro_ch.add_item(doc_style)
        intro_ch.content = """
                <html>
                <head>
                    <title>Introduction</title>
                    <link rel="stylesheet" href="style/main.css" type="text/css" />
                </head>
                <body>
                    <h1>%s</h1>
                    <p><b>By: %s</b></p>
                    <p>%s</p>
                    <p>%s</p>
                </body>
                </html>
                """ % (self.fanfic.title, self.fanfic.author_id, ",".join(self.fanfic.fandoms), self.fanfic.genre)
        book.add_item(intro_ch)

        chapters = []
        for i, chapter in enumerate(self.fanfic.chapters):
            # create chapter
            c1 = epub.EpubHtml(title=chapter.title, file_name='chapter_%s.xhtml' % i, lang='en')
            c1.content = chapter.raw_text

            # add chapter
            book.add_item(c1)

            chapters.append(c1)

        # define Table Of Contents
        book.toc = (
            epub.Link('intro.xhtml', 'Introduction', 'intro'),
            (epub.Section('Chapters'), chapters)
        )

        # add default NCX and Nav file
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # define CSS style
        style = 'BODY {color: white;}'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)

        # add CSS file
        book.add_item(nav_css)

        # basic spine
        # Create spine
        nav_page = epub.EpubNav(uid='book_toc', file_name='toc.xhtml')
        book.add_item(nav_page)
        book.spine = [intro_ch, nav_page] + chapters

        # write to the file
        filename = os.path.expanduser(iBOOKS_PATH) + '%s.epub' % self.fanfic.title
        print("Saving to %s" % filename)
        if path.exists(filename):
            remove(filename)
        epub.write_epub(filename, book, {})
        return filename

if __name__ == "__main__":
    convert = Converter(12306614)
    convert.convert_to_epub()
