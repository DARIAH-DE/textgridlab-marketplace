from app.main import load_data

def test_main_api_p(test_app):
    response = test_app.get('/marketplace/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_catalog_api_p(test_app):
    response = test_app.get('/marketplace/catalogs/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_taxonomy_term_api_p(test_app):
    response = test_app.get('/marketplace/taxonomy/term/tg01,4/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_list_type_api_p(test_app):
    response = test_app.get('/marketplace/featured/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_list_type_market_api_p(test_app):
    response = test_app.get('/marketplace/featured/0/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_recent_api_p(test_app):
    response = test_app.get('/marketplace/recent/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_favourites_api_p(test_app):
    response = test_app.get('/marketplace/favorites/top/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_popular_api_p(test_app):
    response = test_app.get('/marketplace/popular/top/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_node_api_p(test_app):
    response = test_app.get('/marketplace/node/1/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'

def test_content_api_p(test_app):
    response = test_app.get('/marketplace/content/1/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml'
    #assert response.mimetype == 'text/xml'

# TODO: ^content/(.*?)$ / ^api/p/search/apachesolr_search/(.*?)$ / ^$ <INSERT URL HERE>/cgi-bin/msInterface.cgi?action=goto_wiki

def test_404(test_app):
    response = test_app.get('/marketplace/nopage')
    assert response.status_code == 404
    assert response.headers['Content-Type'] == 'text/html; charset=utf-8'

def test_check_urls_all_ok(test_app, requests_mock):
    requests_mock.get(
        'http://testserver/marketplace/check', real_http=True
    )

    plugins = load_data()
    for plugin in plugins:
        requests_mock.get(
            plugin.update_url, status_code=200
        )

    response = test_app.get('/marketplace/check')
    assert response.status_code == 200

def test_check_urls_404(test_app, requests_mock):
    requests_mock.get(
        'http://testserver/marketplace/check', real_http=True
    )

    plugins = load_data()
    for plugin in plugins:
        requests_mock.get(
            plugin.update_url, status_code=404
        )

    response = test_app.get('/marketplace/check')
    assert response.status_code == 500