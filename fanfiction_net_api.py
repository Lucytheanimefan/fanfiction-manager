import re, requests, bs4, unicodedata
from datetime import timedelta, date, datetime
from time import time
import plistlib
from file_converter import *

# Constants
root = 'https://www.fanfiction.net'

# REGEX MATCHES

# STORY REGEX
_STORYID_REGEX = r"var\s+storyid\s*=\s*(\d+);"
_CHAPTER_REGEX = r"var\s+chapter\s*=\s*(\d+);"
_CHAPTERS_REGEX = r"Chapters:\s*(\d+)\s*"
_WORDS_REGEX = r"Words:\s*([\d,]+)\s*"
_TITLE_REGEX = r"var\s+title\s*=\s*'(.+)';"
_DATEP_REGEX = r"Published:\s*<span.+?='(\d+)'>"
_DATEU_REGEX = r"Updated:\s*<span.+?='(\d+)'>"

# USER REGEX
_USERID_REGEX = r"var\s+userid\s*=\s*(\d+);"
_AUTHOR_REGEX = r"href='/u/\d+/(.+?)'"
_USERID_URL_EXTRACT = r".*/u/(\d+)"
_USERNAME_REGEX = r"<link rel=\"canonical\" href=\"//www.fanfiction.net/u/\d+/(.+)\">"
_USER_STORY_COUNT_REGEX = r"My Stories\s*<span class=badge>(\d+)<"
_USER_FAVOURITE_COUNT_REGEX = r"Favorite Stories\s*<span class=badge>(\d+)<"
_USER_FAVOURITE_AUTHOR_COUNT_REGEX = r"Favorite Authors\s*<span class=badge>(\d+)<"

# Useful for generating a review URL later on
_STORYTEXTID_REGEX = r"var\s+storytextid\s*=\s*storytextid=(\d+);"

# REGEX that used to parse reviews page
_REVIEW_COMPLETE_INFO_REGEX = r"img class=.*?</div"
_REVIEW_USER_NAME_REGEX = r"> *([^< ][^<]*)<"
_REVIEW_CHAPTER_REGEX = r"<small style=[^>]*>([^<]*)<"
_REVIEW_TIME_REGEX = r"<span data[^>]*>([^<]*)<"
_REVIEW_TEXT_REGEX = r"<div[^>]*>([^<]*)<"

# Used to parse the attributes which aren't directly contained in the
# JavaScript and hence need to be parsed manually
_NON_JAVASCRIPT_REGEX = r'Rated:(.+?)</div>'
_HTML_TAG_REGEX = r'<.*?>'

# Needed to properly decide if a token contains a genre or a character name
_GENRES = [
    'General', 'Romance', 'Humor', 'Drama', 'Poetry', 'Adventure', 'Mystery',
    'Horror', 'Parody', 'Angst', 'Supernatural', 'Suspense', 'Sci-Fi',
    'Fantasy', 'Spiritual', 'Tragedy', 'Western', 'Crime', 'Family', 'Hurt',
    'Comfort', 'Friendship'
]

# TEMPLATES
_STORY_URL_TEMPLATE = 'https://www.fanfiction.net/s/%d'
_CHAPTER_URL_TEMPLATE = 'https://www.fanfiction.net/s/%d/%d'
_USERID_URL_TEMPLATE = 'https://www.fanfiction.net/u/%d'

_DATE_COMPARISON = date(1970, 1, 1)


def _parse_string(regex, source):
    """Returns first group of matched regular expression as string."""
    return re.search(regex, source).group(1)


def _parse_integer(regex, source):
    """Returns first group of matched regular expression as integer."""
    match = re.search(regex, source).group(1)
    match = match.replace(',', '')
    return int(match)


def _parse_date(regex, source):
    xutime = _parse_integer(regex, source)
    delta = timedelta(seconds=xutime)
    return _DATE_COMPARISON + delta


def _unescape_javascript_string(string_):
    """Removes JavaScript-specific string escaping characters."""
    return string_.replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\')


def _visible_filter(element):
    if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
        return False
    element = unicodedata.normalize('NFKD', element).encode('ascii', 'ignore')
    if re.match(r'<!--.*-->', str(element)):
        return False
    return True


def _get_int_value_from_token(token, prefix):
    if not token.startswith(prefix):
        raise ValueError("int token doesn't starts with given prefix")
    else:
        return int(token[len(prefix):].replace(',', ''))


def _get_date_value_from_token(token, prefix):
    if not token.startswith(prefix):
        raise ValueError("date token doesn't starts with given prefix")
    else:
        try:
            return datetime.strptime(token[len(prefix):], '%m/%d/%Y')
        except ValueError:
            return datetime.now()


def _get_key_of_first_positive(f, d):
    """
    returns key k of first item in l for which f(k) == True
    or None
    """
    for key, value in d.items():
        if f(key) == True:
            return key
    return None


class Story(object):
    def __init__(self, id=None):
        """ A story on fanfiction.net

        If both url, and id are provided, url is used.

        :type id: int
        :param url: The url of the story.
        :param id: The story id of the story.

        Attributes:
            id  (int):              The story id.
            timestamp:              The timestamp of moment when data was consistent with site
            fandoms [str]:           The fandoms to which the story belongs
            chapter_count (int);    The number of chapters.
            word_count (int):       The number of words.
            author_id (int):        The user id of the author.
            title (str):            The title of the story.
            date_published (date):  The date the story was published.
            date_updated (date):    The date of the most recent update.
            rated (str):            The story rating.
            language (str):         The story language.
            genre [str]:            The genre(s) of the story.
            characters [str]:       The character(s) of the story.
            reviews (int):          The number of reviews of the story.
            favs (int):             The number of user which has this story in favorite list
            followers (int):        The number of users who follow the story
            complete (bool):        True if the story is complete, else False.
        """
        self.id = id
        if id is None:
            raise ValueError("id can't be None")

    def download_data(self):
        self.timestamp = datetime.now()
        url = _STORY_URL_TEMPLATE % int(self.id)
        source = requests.get(url)
        source = source.text
        self._soup = bs4.BeautifulSoup(source, 'html.parser')

        self.author_id = _parse_integer(_USERID_REGEX, source)
        self.title = _unescape_javascript_string(_parse_string(_TITLE_REGEX, source).replace('+', ' '))
        print('download_data({})'.format(self.id))
        fandom_chunk = self._soup.find('div', id='pre_story_links').find_all('a')[-1].get_text().replace('Crossover',
                                                                                                         '')
        self.fandoms = [fandom.strip() for fandom in fandom_chunk.split('+')]

        del self._soup

        # Tokens of information that aren't directly contained in the
        # JavaScript, need to manually parse and filter those
        with open('source', 'w') as f:
            f.write(source)
        descr = re.search(_NON_JAVASCRIPT_REGEX, source.replace('\n', ' ')).group(0)
        tokens = [token.strip() for token in
                  re.sub(_HTML_TAG_REGEX, '', descr).split('-')]
        self._parse_description(tokens)

    def _parse_description(self, tokens):
        """
        parse desription of story such as 'Rated: T - English - Humor/Adventure - Chapters: 2 - Words: 131,097 - Reviews: 537 - Favs: 2,515 - Follows: 2,207 - Updated: Jul 27, 2016 - Published: Dec 17, 2009 - Harry P.'
        splitted into tokens list by '-' character
        This functions fill all field of the self object except: id, author_id, title, fandoms, timestamp
        """
        # print('parse_descr({})'.format(tokens))
        # skipping tokens 'Crossover' and token which contains fandoms
        while not tokens[0].startswith('Rated:'):
            tokens = tokens[1:]

        # Both tokens are constant and always available
        self.rated = tokens[0].replace('Rated:', '').replace('Fiction', '').strip()
        self.language = tokens[1]

        tokens = tokens[2:]

        # there can be token with the list of genres
        if tokens[0] in _GENRES or '/' in tokens[0] and all(token in _GENRES for token in tokens[0].split('/')):
            self.genre = tokens[0].split('/')
            tokens = tokens[1:]
        else:
            self.genre = []

        # deleting useless 'id: ...' token
        if tokens[-1].startswith('id:'):
            tokens = tokens[:-1]

        # and if story is complete the last token contain 'Complete'
        if 'Complete' in tokens[-1]:
            self.complete = True
            tokens = tokens[:-1]
        else:
            self.complete = False

        # except those there are 4 possible kind of tokens: tokens with int data, tokens with date data, story id token,
        # and token with characters/pairings
        int_tokens = {'Chapters: ': 'chapter_count', 'Words: ': 'word_count', 'Reviews: ': 'reviews',
                      'Favs: ': 'favs', 'Follows: ': 'followers'}
        date_tokens = {'Updated: ': 'date_updated', 'Published: ': 'date_published'}

        for token in tokens:
            int_k = _get_key_of_first_positive(lambda s: token.startswith(s), int_tokens)
            date_k = _get_key_of_first_positive(lambda s: token.startswith(s), date_tokens)
            if int_k is not None:
                setattr(self, int_tokens[int_k], _get_int_value_from_token(token, int_k))
            elif date_k is not None:
                setattr(self, date_tokens[date_k], _get_date_value_from_token(token, date_k))
            else:
                self.characters = [c.translate(str.maketrans('', '', '[]')).strip() for c in token.split(',')]

        # now we have to fill field which could be left empty
        if not hasattr(self, 'chapter_count'):
            self.chapter_count = 1

        for field in int_tokens.values():
            if not hasattr(self, field):
                setattr(self, field, 0)

        if not hasattr(self, 'date_updated'):
            self.date_updated = self.date_published

        if not hasattr(self, 'characters'):
            self.characters = []

    def _parse_from_storylist_format(self, story_chunk):
        """
        Parse story from html chunk
        """
        self.timestamp = datetime.now()
        self.fandoms = [s.strip() for s in story_chunk.get('data-category').split('&')]
        self.title = story_chunk.get('data-title')

        self.author_id = _parse_integer(_USERID_URL_EXTRACT, str(story_chunk))

        descr = story_chunk.find('div', {'class': 'z-padtop2 xgray'}).get_text()
        self._parse_description([token.strip() for token in descr.split('-')])

    def get_chapters(self):
        """
        A generator for all chapters in the story.
        :return: A generator to fetch chapter objects.
        """
        try:
            for number in range(1, self.chapter_count + 1):
                yield Chapter(story_id=self.id, chapter=number)
        except KeyboardInterrupt:
            print("!-- Stopped fetching chapters")

    def get_user(self):
        """
        :return: The user object of the author of the story.
        """
        return User(id=self.author_id)

    def print_info(self, attrs=['title', 'id', 'fandoms', 'author_id', 'chapter_count', 'word_count', 'date_published',
                                'date_updated', 'rated', 'language', 'genre', 'characters', 'reviews', 'favs',
                                'followers', 'complete']):
        """
        Print information held about the story.
        :param attrs: A list of attribute names to print information for.
        :return: void
        """
        for attr in attrs:
            print("%12s\t%s" % (attr, getattr(self, attr)))

    def get_reviews(self):
        """
        A generator for all reviews in the story.
        :return: A generator to fetch reviews.
        """
        return ReviewsGenerator(self.id)

    # def download(self, output='', message=True, ext=''):
    #     download(self, output=output, message=message, ext=ext)

    # Method alias which allows the user to treat the get_chapters method like
    # a normal property if no manual opener is to be specified.
    chapters = property(get_chapters)


class ReviewsGenerator(object):
    """
    Class that generates review in chronological order
    Attributes:
        base_url            (int):      storys review url without specified page number
        page_number         (int):      number of current review page
        reviews_cache       List(str):  list of already downloaded  (and partially processed) reviews
        skip_reviews_number (int):      length of already processed review from review_cache
    """

    def __init__(self, story_id, chapter=0):
        """
        If chapter unspecified then generator generates review for all chapters
        """
        self.story_id = story_id
        self.base_url = root + '/r/' + str(story_id) + '/' + str(chapter) + '/'

    def __iter__(self):
        self.page_number = 0
        self.reviews_cache = []
        self.skip_reviews_number = 0
        return self

    def __next__(self):
        self.skip_reviews_number += 1
        if len(self.reviews_cache) >= self.skip_reviews_number:
            return Review(self.story_id, self.reviews_cache[self.skip_reviews_number - 1])

        self.page_number += 1
        page = self._downloadReviewPage(self.page_number)
        self.reviews_cache = re.findall(_REVIEW_COMPLETE_INFO_REGEX, page, re.DOTALL)

        if len(self.reviews_cache) == 0:
            raise StopIteration

        self.skip_reviews_number = 1
        return Review(self.story_id, self.reviews_cache[0])

    def _downloadReviewPage(self, page_number):
        url = self.base_url + str(page_number) + '/'
        return requests.get(url).text


class Review(object):
    """
    A single review of fanfiction story, on fanfiction.net
    Attributes:
        story_id    (int):  story ID
        user_id     (int):  ID of user who submited review (may be None if review is anonymous)
        user_name   (str):  user name (or pseudonym for anonymous review)
        chapter     (str):  chapter name
        time_ago    (str):  how much time passed since review submit (format may be inconsistent with what you see in browser just because fanfiction.net sends different pages depend on do you download page from browser or from console/that library
        text        (str):  review text
    """

    def __init__(self, story_id, unparsed_info):
        """
        That method should not be invoked outside of Story and Chapter classes
        :param story_id         (int):  story ID
        :param unparsed_info    (int):  string that contain the rest info
        """
        self.story_id = story_id
        self.user_name = _parse_string(_REVIEW_USER_NAME_REGEX, unparsed_info)
        self.chapter = _parse_string(_REVIEW_CHAPTER_REGEX, unparsed_info)
        self.text = _parse_string(_REVIEW_TEXT_REGEX, unparsed_info)

        self.time_ago = _parse_string(_REVIEW_TIME_REGEX, unparsed_info)

        # fanfiction.net provide strange format, instead of '8 hours ago' it show '8h'
        # so let's add ' ago' suffix if review submitted hours or minutes ago
        if self.time_ago[-1] == 'h' or self.time_ago[-1] == 'm':
            self.time_ago += ' ago'

        if re.search(_USERID_URL_EXTRACT, unparsed_info) == None:
            self.user_id = None
        else:
            self.user_id = _parse_integer(_USERID_URL_EXTRACT, unparsed_info)


class Chapter(object):
    def __init__(self, url=None, story_id=None, chapter=None):
        """ A single chapter in a fanfiction story, on fanfiction.net

        :param url: The url of the chapter.
        :param story_id: The story id of the story of the chapter.
        :param chapter: The chapter number of the story.

        Attributes:
            story_id    (int):  Story ID
            number      (int):  Chapter number
            story_text_id (int):    ?
            title       (str):  Title of the chapter, or title of the story.
            raw_text    (str):  The raw HTML of the story.
            text_list   List(str):  List of unicode strings for each paragraph.
            text        (str):  Visible text of the story.
        """

        if url is None:
            if story_id is None:
                print('A URL or story id must be entered.')
            elif chapter is None:
                print('Both a story id and chapter number must be provided')
            elif story_id and chapter:
                url = _CHAPTER_URL_TEMPLATE % (story_id, chapter)

        source = requests.get(url)
        source = source.text
        self.story_id = _parse_integer(_STORYID_REGEX, source)
        self.number = _parse_integer(_CHAPTER_REGEX, source)
        self.story_text_id = _parse_integer(_STORYTEXTID_REGEX, source)

        soup = bs4.BeautifulSoup(source, 'html.parser')
        select = soup.find('select', {'name': 'chapter'})
        if select:
            # There are multiple chapters available, use chapter's title
            found = select.find('option', selected=True)
            if found:
                print(found)
                self.title = str(found).partition("<option value=\"")[0].split(">", 1)[1].split("<", 1)[0] #found[0].text #.split(None, 1)[1]
        else:
            # No multiple chapters, one-shot or only a single chapter released
            # until now; for the lack of a proper chapter title use the story's
            self.title = _unescape_javascript_string(_parse_string(_TITLE_REGEX, source)).decode()
        soup = soup.find('div', id='storytext')
        # Try to remove AddToAny share buttons
        try:
            soup.find('div', {'class': lambda class_: class_ and 'a2a_kit' in class_}).extract()
        except AttributeError:
            pass
        # Normalize HTML tag attributes
        for hr in soup('hr'):
            del hr['size']
            del hr['noshade']

        self.raw_text = soup.decode()

        texts = soup.findAll(text=True)
        self.text_list = list(filter(_visible_filter, texts))
        self.text = '\n'.join(self.text_list)

    def get_reviews(self):
        """
        A generator for all reviews for that chapter
        :return: A generator to fetch reviews.
        """
        return ReviewsGenerator(self.story_id, self.number)


class User(object):
    def __init__(self, url=None, id=None):
        """ A user page on fanfiction.net

        :param url: The url of user profile.
        :param id: The url of user profile.

        Attributes:
            id                     (int): User id
            timestamp              (int): Timestamp of last update of downloaded profile
            favorite_stories List(Story): The list of user favorite stories
            username               (str): The username
            story_count            (int): The number of stories written by user
            favourite_count        (int): The number of stories favourited by user
            favourite_author_count (int): The number of authors favourited by user
        """
        if url is None:
            if id is None:
                raise ValueError("Either url or id must be specified.")
            else:
                self.id = id
        else:
            self.id = _parse_integer(_USERID_URL_EXTRACT, url)

    def download_data(self):
        self.timestamp = time()
        url = _USERID_URL_TEMPLATE % self.id
        source = requests.get(url)
        source = source.text
        self._soup = bs4.BeautifulSoup(source, 'html.parser')
        self.url = url
        self.username = _parse_string(_USERNAME_REGEX, source)
        try:
            self.story_count = _parse_integer(_USER_STORY_COUNT_REGEX, source)
        except AttributeError:
            self.story_count = 0
        try:
            self.favourite_count = _parse_integer(_USER_FAVOURITE_COUNT_REGEX, source)
        except AttributeError:
            self.favourite_count = 0
        try:
            self.favourite_author_count = _parse_integer(_USER_FAVOURITE_AUTHOR_COUNT_REGEX, source)
        except AttributeError:
            self.favourite_author_count = 0
        self._set_favourite_stories()

    def get_stories(self):
        """
        Get the stories written by this author.
        :return: A generator for stories by this author.
        """
        xml_page_source = requests.get(root + '/atom/u/%d/' % self.id)
        xml_page_source = xml_page_source.text
        xml_soup = bs4.BeautifulSoup(xml_page_source, 'html.parser')
        entries = xml_soup.findAll('link', attrs={'rel': 'alternate'})
        for entry in entries:
            story_url = entry.get('href')
            yield Story(story_url)

    def _set_favourite_stories(self):
        favourite_stories = self._soup.findAll('div', {'class': 'favstories'})
        self.favorite_stories = []
        for story_chunk in favourite_stories:
            story = Story(id=story_chunk.get('data-storyid'))
            story._parse_from_storylist_format(story_chunk)
            self.favorite_stories.append(story)

    def _clean_unparsed_data(self):
        del self._soup

    def get_favourite_authors(self):
        """
        :return: User generator for the favourite authors of this user.
        """
        tables = self._soup.findAll('table')
        table = tables[-1]
        author_tags = table.findAll('a', href=re.compile(r".*/u/(\d+)/.*"))
        for author_tag in author_tags:
            author_url = author_tag.get('href')
            author_url = root + author_url
            yield User(author_url)


# Searching constants

# Sort by:
UPDATE_DATE = 1
PUBLISH_DATE = 2
REVIEWS = 3
FAVORITES = 4
FOLLOW = 5

# Rating
ALL = 10
MATURE = 4
T = 3

MIN_FOLLOW_TO_CHAPTER_RATIO = 15

iBOOKS_FILE_PATH = "/Users/lucyzhang/Library/Containers/com.apple.BKAgentService/Data/Documents/iBooks/Books/Books.plist"


class FanFiction:

    @staticmethod
    def get_recommendations(fandom_title, medium="anime", character="", sort_by=FOLLOW, rating=ALL, download_num=0):
        url = root + "/%s/%s/?srt=%i&r=%i&c1=%s" % (medium, fandom_title, sort_by, rating, character)
        print(url)
        r = requests.get(url)
        source = r.text
        soup = bs4.BeautifulSoup(source, 'html.parser')
        story_list = soup.find_all("div", {"class": "z-list"})

        recommended_story_ids = []

        for i, story in enumerate(story_list):
            title = story.find("a", {"class": "stitle"})
            story_id = re.search('/s/(.*)/1/', title['href']).group(1)
            description = story.find("div", {"class": "z-indent"})
            other_info = description.find("div", {"class": "z-padtop2"})
            follows = re.search('Follows: (.*) - Updated', other_info.text).group(1)
            chapters = re.search('Chapters: (.*) - Words', other_info.text).group(1)
            follow_to_chapter = int(follows.replace(',', ''))/int(chapters.replace(',', ''))
            if follow_to_chapter > MIN_FOLLOW_TO_CHAPTER_RATIO:
                recommended_story_ids.append(story_id)
                if i <= download_num and not FanFiction.fanfic_epub_already_exists(title):
                    converter = Converter(int(story_id))
                    converter.convert_to_epub()
        return recommended_story_ids

    @staticmethod
    def fanfic_epub_already_exists(fanfic_title):
        pl = plistlib.readPlist(iBOOKS_FILE_PATH)
        books = pl["Books"]
        for book in books:
            title = book["itemName"]
            if fanfic_title == title:  # Should do a better check with the story id instead
                print(title + " ALREADY EXISTS IN iBOOKS!")
                return True
        return False


if __name__ == "__main__":
    # print(FanFiction.get_recommendations("Death-Note", download_num=10))
    FanFiction.fanfic_epub_already_exists("Twenty-Three Percent")
