from flask import Flask, render_template, redirect, flash, url_for, request, session, send_from_directory, send_file
from flask_cors import cross_origin
#
import datetime
import requests
import json
#
from db_connection import Users, DB_User, Provider
from report_doc import render_docx_template


app = Flask(__name__)
app.secret_key = 'admin'

TABLES = ['book', 'periodical', 'libraries', 'udk', 'book_fund', 
          'periodical_fund', 'read_room', 'reader', 'rent_book']
TOOLS = ['sql', 'procedure', 'doc', 'export_json']
PROCEDURS = []

@app.route("/")
def root():
    if session.get('role'):
        return redirect(url_for("library"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method != "POST":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]
    DB_User(username, password)

    try:
        Provider.perform(lambda cur: cur.execute("SELECT * FROM current_user"))
        if user := Users.raw(username):
            session["role"] = user.name
            return redirect(url_for("library"))
        
        return render_template("login.html", error = "Незарегистрированный пользователь: %s" % (username))
    except:
        return render_template("login.html", error = "Ошибка доступа!")


@app.route("/library", methods=["GET", "POST"])
@cross_origin(origins=['https://api.forismatic.com'])
def library():

    url = "https://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang=ru"
    response = requests.get(url)
    data = response.json()
    quote = data['quoteText']
    author = data['quoteAuthor']
    
    if session.get('role') == Users.admin.name:
        return render_template("library.html", tools=TOOLS, tables=TABLES, quote=quote, author=author)
    return render_template("library.html", tools=[], tables=TABLES[:4], quote=quote, author=author)


@app.route("/library/<table>")
def library_view(table):

    @Provider.perform
    def select(cur):
        cur.execute("SELECT * FROM %s" % (table))
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return value, columns

    try:
        data, columns = select()
        session['table'] = table
        session['columns'] = columns

        if session.get('role') == Users.reader.name :
            return render_template("view.html", table=table, columns=columns, data=data, error=None)
        
        return render_template("admin/view.html", table=table, columns=columns, data=data, error=None)
    except Exception as error:
        return render_template("view.html", table=None, columns=None, data=None, error=error)


@app.route("/library/<int:row_id>", methods=["DELETE"])
def delete_row(row_id):
    table = session.get('table')
    key = session.get('columns')[0]
    try:
        Provider.perform(lambda cur: 
            cur.execute("DELETE FROM %s WHERE %s = %s" % (table, key, row_id)))
        return "Успешно удалено.", 200
    except Exception as error:
        return "Ошибка удаления: %s", (error)


@app.route("/library/<table>/append", methods=["GET", "POST"])
def append_row(table):
    if request.method != "POST":
        return redirect(url_for("library_view", table=table))

    values = []
    columns = []

    @Provider.perform
    def insert(cur):
        parametr = lambda list: ','.join(map(str, list))
        try:
            cur.execute("INSERT INTO %s (%s) values (%s)" % (table, parametr(columns), parametr(values)))
        except Exception as error:
            print(error)

    try:
        for item, value in request.form.items():
            if value:
                values.append(value)
                columns.append(item)
        insert()

        return redirect(url_for("library_view", table=table))
    except Exception as error:
         print(error)
         return "Ошибка добавления: %s", (error)


@app.route("/library/<path:change>", methods=["UPDATE"])
def change_row(change):
    id, column, value = change.split('.')
    table = session.get('table')
    columns = session.get('columns')

    @Provider.perform
    def insert(cur):
        cur.execute("""
        UPDATE %s 
           SET %s = '%s'
         WHERE %s = %s;
        """ % (table, columns[int(column)], value, columns[0], id))

    try:
        insert()
        return "Успешно изменино.", 200
    except Exception as error:
        return "Ошибка изменения: %s" % (error)


@app.route("/library/sql", methods=["GET", "POST"])
def sql():
    if request.method != "POST":
        return render_template("admin/sql.html", data=None, error=None)

    @Provider.perform
    def sql(cur):
        cur.execute(request.form["query"])
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return value, columns

    try:
        data, columns = sql()
        return render_template("admin/sql.html", data=data, error=None) 
    except Exception as error:
        return render_template("admin/sql.html", data=None, error=error)


@app.route("/library/procedure", methods=["GET", "POST"])
def procedure():
    return render_template('admin/procedure.html', procedurs=PROCEDURS)


@app.route("/library/procedure/is_empty_book", methods=["POST"])
def is_empty_book():
    
    book = request.form['book']
    library = request.form['library']
    
    @Provider.perform
    def procedure(cur):
        cur.execute('CALL is_empty_book(%s, %s)' % (book, library))
        return cur.fetchone()

    try:
        response = procedure()

        return response
    except Exception as error:
        return "Ошибка: %s" % (error) 


@app.route("/library/doc", methods=["GET", "POST"])
def doc():
    docxs = ['reminder', 'restoration_book', 'books_udk']
    return render_template('admin/doc.html', docxs=docxs)


@app.route("/library/doc/<docx>", methods=["GET", "POST"])
def docx(docx):
    
    @Provider.perform
    def select(cur):
        cur.execute('SELECT * FROM %s()' % (docx))
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return columns, value

    try:
        columns, value = select()
        grafs()
        doc = render_docx_template(docx, columns, value)
        return send_file(doc, as_attachment=False)
    except Exception as error:
        print(error)
        return redirect(url_for("doc"))


@app.route("/library/json", methods=["GET", "POST"])
def export_json():
    return render_template("admin/export_json.html", tables=TABLES)


@cross_origin(origins=['http://127.0.0.1:5000'])
@app.route("/library/json/<table>", methods=["GET", "POST"])
def export_json_table(table):
    
    @Provider.perform
    def select(cur):
        cur.execute("SELECT * FROM %s" % (table))
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return value, columns
    
    def convert_date(obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        raise TypeError("Type not serializable")

    try:
        data, keys = select()
        dict_data = [dict(zip(keys, item)) for item in data]
        json_data = json.dumps(dict_data, default=convert_date, ensure_ascii=False, indent=4)
        return json_data
    except Exception as erro:
        return 'Ошибка: %s' % erro


if __name__ == "__main__":
    app.run(debug=True)