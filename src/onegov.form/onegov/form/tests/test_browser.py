def test_snippets(browser):
    browser.visit('/snippets')

    assert browser.is_element_present_by_css('.formcode-snippets')
    assert len(browser.find_by_css('.formcode-toolbar')) == 1

    assert not browser.find_by_css('.formcode-snippet')
    browser.find_by_css('.formcode-toolbar-element').click()

    assert browser.find_by_css('.formcode-snippet')
    browser.find_by_css('.formcode-toolbar-element').click()

    assert not browser.find_by_css('.formcode-snippet')
    browser.find_by_css('.formcode-toolbar-element').click()

    browser.find_by_css('.formcode-snippet-optional').click()
    assert '= ___' in browser.find_by_css('textarea').value

    assert not browser.find_by_css('.formcode-snippet')
    browser.find_by_css('.formcode-toolbar-element').click()

    browser.find_by_css('.formcode-snippet-required').click()
    assert '*= ___' in browser.find_by_css('textarea').value
