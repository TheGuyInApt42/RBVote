from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from time import sleep
import datetime
from pymongo import MongoClient
import pygn
import cPickle as pickle


class GracenoteAPI:
    def __init__(self):
        """
        Initiliazes api object with client ID
        contains method to register client ID to get userID
        contains method to save userID so do not have to keep recalling/registering id w/ each api call
        contains method to load userID from system
        """
        self.clientID = '1697825127-FFAF0005CD2F8CD3C03A6B5B6CF81EBD'
        self.userID = ''
        self.registered_id = ''

    def register(self):
        """
        Registers with Gracenote api to get userID
        stores registeredID in instance var
        """
        self.registered_id = pygn.register(self.clientID)

    def save_userID(self):
        """
        Saves userID to system with pickling
        """
        self.register()
        pickle.dump(self.registered_id, open('userID.p', 'wb'))

    def load_userID(self):
        """
        Loads userID from system and stores it in instance var
        """
        userID = pickle.load(open('userID.p', 'rb'))
        self.userID = userID


class Voter:
    def __init__(self):
        self.url = 'http://www.harmonixmusic.com/games/rock-band/request/'  # URL for Harmonix Song request
        self.song_db_url = 'http://rbchronicle.net/'  # URL for Rock Band song database

    def load_site(self):
        try:
            browser = webdriver.PhantomJS()
            browser.get(self.url)
            return browser
        except Exception, e:
            print str(e)

    @staticmethod
    def complete_form(site, song, artist):
        """
        Fills out form with song and artist and submits
        :param site: browser object to perform operations on
            :type: WebDriver()
        :param song: name of song to vote for
            :type: str
        :param artist: song artist
            :type: str
        """
        site.find_element_by_id('id_title').send_keys(song)
        site.find_element_by_id('id_artist').send_keys(artist)
        site.find_element_by_css_selector('.button').click()

    def check_songs_in_game(self, artist):
        """
        Given artist, checks the database for songs that they have currently in game
        :param artist: name of artist to check songs that they have in game
            :type: str
        :rtype: list
        """
        songs_in_game = []
        driver = webdriver.PhantomJS('phantomjs')
        driver.set_window_size(1120, 550)
        driver.implicitly_wait(40)
        driver.get(self.song_db_url)

        search_box = driver.find_element_by_css_selector("#quicksearch-inputEl")
        search_box.send_keys(artist)
        search_box.send_keys(Keys.ENTER)

        rows = driver.find_elements_by_xpath('//*[@id="gridview-1021-body"]/tr/td')
        for row in range(1, len(rows)+1, 12):
            songs_in_game.append(rows[row].text)

        return songs_in_game

    def get_discography(self, artists):
        """
        :param artists: list of artists to get discography for
            :type: list

        :rtype: set
        """
        api = GracenoteAPI()
        userID = pickle.load(open('userID.p', 'rb'))

        tracklist = set()
        artist_discography_list = []
        list_of_songs_with_artists = []
        in_game_songs = []
        for band in artists:
            in_game_songs.append(self.check_songs_in_game(band))
            artist_discography_list.append(pygn.get_discography(api.clientID, userID, band, 1, 30))

        for artist_discog in artist_discography_list:
            for release in artist_discog:
                if release['album_artist_name'].lower() in artists:
                    for track in release['tracks']:
                        songs_with_artist = (release['album_artist_name'], track['track_title'])
                        list_of_songs_with_artists.append(songs_with_artist)

        for pair in list_of_songs_with_artists:
            tracklist.add(pair)

        for t in tracklist.copy():
            for song in in_game_songs:
                for title in song:
                    if title in t[1]:
                        tracklist.discard(t)

        return tracklist

    @staticmethod
    def connect_db(title, artist):
        voted_at = datetime.datetime.now()
        timestamp = voted_at.strftime('%m/%d/%y %I:%M:%S%p')
        song = {'artist': artist,
                'title': title,
                'date': timestamp
                }
        client = MongoClient()
        db = client.rock_band_votes
        songs = db.songs
        songs.insert(song)

    def manual_voter(self):
        song_title = raw_input('What is the song name: ')
        artist = raw_input('Who is the artist: ')
        site = self.load_site()
        self.complete_form(site, song_title, artist)

        try:
            voted_already = site.find_element_by_xpath('/html/body/div/div/div[1]/div/div[1]/p')
            if voted_already:
                print 'Too soon to vote for %s' % song_title
                self.run_voter()
        except Exception:
            thanks_button = site.find_element_by_xpath('/html/body/div/div/div[1]/div/a')
            thanks_button.click()
            #self.connect_db(song_title, artist)
            print '%s by %s logged' % (song_title, artist)

    def auto_voter(self):
        """


        """
        artists = []
        maxArtists = 1
        while len(artists) < maxArtists:
            artist = raw_input('Which artist would you like to vote for: ')
            artists.append(artist)
        for band in artists:
            print 'Going to vote for %s' % band
        songs = self.get_discography(artists)
        song_amt = len(songs)
        site = self.load_site()
        for num, song in enumerate(songs):
            self.complete_form(site, song[1], song[0])

            try:
                voted_already = site.find_element_by_xpath('/html/body/div/div/div[1]/div/div[1]/p')
                if voted_already:
                    print 'Too soon to vote for %s' % song[1]
                    sleep(10)
                    self.run_voter()

            except Exception:
                # self.connect_db(song[1], song[0])
                print '%s by %s logged (%s/%s)' % (song[1], song[0], num+1, song_amt)
                thanks_button = site.find_element_by_xpath('/html/body/div/div/div[1]/div/a')
                thanks_button.click()

                sleep(20)


v = Voter()
v.auto_voter()
# v.manual_voter()




