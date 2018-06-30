from fanfiction_net_api import *


class Converter:

    def __init__(self, story_id):
        self.fanfic = Story(story_id)

    def convert(self):
        self.fanfic.download_data()
        self.fanfic.get_chapters()
        print(self.fanfic.chapter_count)
        print("----")
        print(self.fanfic.chapters)

        for chapter in self.fanfic.chapters:
            print(chapter.title)


if __name__ == "__main__":
    convert = Converter(12942457)
    convert.convert()