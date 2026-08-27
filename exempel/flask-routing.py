from flask import Flask, request

app = Flask(__name__)

# Example of a simple GET route that returns a few lines of HTML code
@app.route('/')
def home():
    return '''
            <p>Välkommen till Flask Routing! Testa följande router:</p>
            <ul>
            <li>/user/[username]</li>
            <li>/search?q=[query]</li>
            </ul>
            '''

# Example of GET route with URL parameters. For example http://127.0.0.1:5000/user/holger
@app.route('/user/<username>')
def show_user_profile(username):
    if username== 'holger':
        return f'User: {username}, Hej kära holger'
    print(f"User: {username}") # print to console
    return f'User: {username}, fuck you'


# Example of GET route with query parameters. For example http://127.0.0.1:5000/search?q=flask
@app.route('/search')
def search():
    # request.args contains information from the query string
    query = request.args.get('q', '')
    print(f"Search query: {query}") # print to console
    return f'Search query: {query}'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')