"""Limit canary interactions to the visible board, not retained detail DOM."""
BOARD_CARDS = '#board:not(.hidden) #cards button.pick'
BOARD_GAMES = '#board:not(.hidden) #cards [data-game]'

def verify_board_scope(browser):
    """Synthetic selector regression on its own page, never the deployed app."""
    page = browser.new_page()
    try:
        page.set_content('''<style>.hidden {display:none}</style>
          <section id="detail" class="hidden"><button class="pick" data-game="old">Old NBA detail</button></section>
          <section id="board"><div id="cards"><button class="pick" onclick="this.dataset.clicked='yes'">Current NFL board</button><button data-game="current">Current game</button></div></section>''')
        cards = page.locator(BOARD_CARDS)
        games = page.locator(BOARD_GAMES)
        if cards.count() != 1 or games.count() != 1:
            return False
        cards.first.click()
        if cards.first.get_attribute('data-clicked') != 'yes':
            return False
        page.locator('#board').evaluate("el => el.classList.add('hidden')")
        return page.locator(BOARD_CARDS).count() == 0 and page.locator(BOARD_GAMES).count() == 0
    finally:
        page.close()
