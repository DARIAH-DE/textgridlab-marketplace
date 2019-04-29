def test_main_api_p(client):
    response = client.get('/api/p')
    assert response.status_code == 200
    assert response.mimetype == 'application/xml'
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_catalog_api_p(client):
    response = client.get('/catalogs/api/p')
    assert response.status_code == 200
    assert response.mimetype == 'application/xml'
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_taxonomy_term_api_p(client):
    response = client.get('/taxonomy/term/tg01,4/api/p')
    assert response.status_code == 200
    assert response.mimetype == 'application/xml'
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_list_type_api_p(client):
    response = client.get('/featured/api/p')
    assert response.status_code == 200
    assert response.mimetype == 'application/xml'
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_list_type_market_api_p(client):
    response = client.get('/featured/0/api/p')
    assert response.status_code == 200
    assert response.mimetype == 'application/xml'
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_recent_api_p(client):
    response = client.get('/recent/api/p')
    assert response.status_code == 200
    assert response.mimetype == 'application/xml'
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_favourites_api_p(client):
    response = client.get('/favorites/top/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_popular_api_p(client):
    response = client.get('/popular/top/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_node_api_p(client):
    response = client.get('/node/1/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'

def test_content_api_p(client):
    response = client.get('/content/1/api/p')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'
    assert response.mimetype == 'application/xml'

# TODO: ^content/(.*?)$ / ^api/p/search/apachesolr_search/(.*?)$ / ^$ <INSERT URL HERE>/cgi-bin/msInterface.cgi?action=goto_wiki

def test_404(client):
    response = client.get('/nopage')
    assert response.status_code == 404
    assert response.headers['Content-Type'] == 'text/html; charset=utf-8'