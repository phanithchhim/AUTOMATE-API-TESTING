from flask import Flask, jsonify, request, make_response

app = Flask(__name__)

@app.route('/api/hello')
def hello():
    return 'CMS Portal API', 200


@app.route('/api/debug/ip')
def debug_ip():
    body = {'remoteAddr': request.remote_addr, 'xff': request.headers.get('X-Forwarded-For'), 'verified_remote_ip': True}
    return jsonify(body), 200


@app.route('/api/login', methods=['POST'])
def login():
    body = request.json or {}
    username = body.get('username')
    password = body.get('password')
    if not username:
        return jsonify({'success': False}), 400
    # simple accept configured test user
    if username == 'phanith.chhim' and password == 'Nith@2010':
        resp = make_response(jsonify({'success': True, 'userId': username, 'token': 'test-token'}), 200)
        resp.set_cookie('JSESSIONID', 'mock-session')
        return resp
    return jsonify({'success': False}), 401


@app.route('/api/signout', methods=['POST'])
def signout():
    return jsonify({'success': True}), 200


@app.route('/api/users')
def users_list():
    data = [
        {'userId': 'phanith.chhim', 'id': 'phanith.chhim', 'username': 'Phanith'},
        {'userId': 'roby.va', 'id': 'roby.va', 'username': 'Roby'},
    ]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/users/<uid>')
def get_user(uid):
    if uid == 'notfound':
        return jsonify({'success': False}), 404
    return jsonify({'userId': uid, 'id': uid, 'username': uid}), 200


@app.route('/api/users/<uid>/permissions')
def user_perms(uid):
    return jsonify({'success': True, 'data': [{'permissionId': 1, 'name': 'read'}]}), 200


@app.route('/api/roles')
def roles_list():
    data = [{'roleId': 1, 'id': 1, 'roleName': 'Admin'}]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/roles', methods=['POST'])
def roles_manage():
    body = request.json or {}
    action = body.get('action')
    # accept CREATE/UPDATE/DELETE action simulation
    if action == 'INVALID':
        return jsonify({'success': False}), 400
    # For update, ensure roleId present otherwise create
    if action == 'UPDATE' and not body.get('roleId'):
        return jsonify({'success': False}), 400
    return jsonify({'success': True, 'roleId': body.get('roleId', 999)}), 200


@app.route('/api/roles/permissions', methods=['POST'])
def roles_permissions():
    body = request.json or {}
    if body.get('action') == 'INVALID':
        return jsonify({'success': False}), 400
    return jsonify({'success': True}), 200


@app.route('/api/roles/permissions/1')
def roles_permissions_list():
    return jsonify({'data': []}), 200


@app.route('/api/users/<uid>', methods=['PUT'])
def update_user(uid):
    body = request.json or {}
    # basic validation: must include username or other fields
    if not body:
        return jsonify({'success': False}), 400
    # simulate success
    return jsonify({'success': True, 'userId': uid}), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
