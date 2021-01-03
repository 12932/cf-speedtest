from cf_speedtest import cf_speedtest

def test_country():
	cf_speedtest.get_our_country()

def test_preamble():
	cf_speedtest.preamble()

def test_main():
	assert cf_speedtest.main() == 0

'''
def test_proxy():
	assert cf_speedtest.main(['--proxy', '100.24.216.83:80']) == 0
'''

def test_nossl():
	assert cf_speedtest.main(['--verifyssl', 'False']) == 0