config.load_autoconfig(False)

c.auto_save.session = True

c.completion.shrink = True

c.downloads.position = 'bottom'
c.downloads.remove_finished = 5000
c.downloads.location.remember = False

c.content.javascript.can_open_tabs_automatically = False
c.content.javascript.clipboard = 'access'
c.content.notifications.enabled = False
c.content.pdfjs = True

c.input.insert_mode.auto_enter = True
c.input.insert_mode.auto_leave = True
c.input.insert_mode.auto_load = True

c.scrolling.smooth = True

c.tabs.position = "bottom"
c.tabs.show = "multiple"

c.url.searchengines = {
    'DEFAULT': 'https://duckduckgo.com/?ia=web&q={}',
    '!ad': 'https://www.amazon.de/s?k={}',
    '!ai': 'https://www.amazon.in/s?k={}',
    '!aw': 'https://wiki.archlinux.org/index.php?search={}',
    '!aur': 'https://aur.archlinux.org/packages?O=0&K={}',
    '!d': 'https://duckduckgo.com/?ia=web&q={}',
    '!dd': 'https://thefreedictionary.com/{}',
    '!e': 'https://www.ebay.de/sch/i.html?_nkw={}',
    '!gh': 'https://github.com/search?o=desc&q={}&s=stars',
    '!gist': 'https://gist.github.com/search?q={}',
    '!gi': 'https://www.google.com/search?tbm=isch&q={}&tbs=imgo:1',
    '!gn': 'https://news.google.com/search?q={}',
    '!ig': 'https://www.instagram.com/explore/tags/{}',
    '!m': 'https://www.google.com/maps/search/{}',
    '!r': 'https://www.reddit.com/search?q={}',
    '!t': 'https://www.thesaurus.com/browse/{}',
    '!w': 'https://en.wikipedia.org/wiki/{}',
    '!yt': 'https://www.youtube.com/results?search_query={}'
}

config.source('gruvbox.py')
