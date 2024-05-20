from flask import Flask, render_template, redirect, flash, url_for, request, session, send_from_directory, send_file, flash, get_flashed_messages, make_response
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
          'periodical_fund', 'read_room', 'reader', 'rent_book', 'test']
TOOLS = ['sql', 'procedure', 'doc', 'export_json']

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
        
        flash("Незарегистрированный пользователь: %s" % (username))
        return render_template("login.html")
    except:
        flash("Ошибка доступа!")
        return render_template("login.html")


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

    @Provider.perform_try
    def select(cur):
        cur.execute("SELECT * FROM %s ORDER BY 1" % (table))
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return value, columns

    value, error = select()

    if error:
        flash(error)
        return render_template("view.html", table=None, columns=None, data=None)
    
    session['table'] = table
    session['columns'] = value[1]

    if session.get('role') == Users.reader.name :
        return render_template("view.html", table=table, columns=value[1], data=value[0])
    return render_template("admin/view.html", table=table, columns=value[1], data=value[0])


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
    for item, value in request.form.items():
        if value:
            values.append(value)
            columns.append(item)

    @Provider.perform_try
    def insert(cur):
        parametr = lambda list: ','.join(map(str, list))
        cur.execute("INSERT INTO %s (%s) values (%s)" % (table, parametr(columns), parametr(values)))

    _, error = insert()
    flash(error if error else 'Запись дабавлена.')
    return redirect(url_for("library_view", table=table))


@app.route("/library/<path:change>", methods=["POST"])
def change_row(change):
    id, column, value = change.split('|')
    table = session.get('table')
    columns = session.get('columns')

    @Provider.perform_try
    def insert(cur):
        cur.execute("""
        UPDATE %s 
           SET %s = '%s'
         WHERE %s = %s;
        """ % (table, columns[int(column)], value, columns[0], id))

    _, error = insert()
    if error:
        return "Ошибка изменения: %s" % (error)
    return "Успешно изменино.", 200



@app.route("/library/sql", methods=["GET", "POST"])
def sql():
    if request.method != "POST":
        return render_template("admin/sql.html", data=None)

    @Provider.perform_try
    def sql(cur):
        cur.execute(request.form["query"])
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return value, columns

    value, error = sql()
    flash(error if error else 'Запрос выполнен.')
    return render_template("admin/sql.html", data=value) 


@app.route("/library/procedure", methods=["GET", "POST"])
def procedure():
    procedures = [('add_book', ['library', 'book', 'count']),
                  ('return_book', ['reade_card', 'book', 'rent_state'])]
    return render_template('admin/procedure.html', procedurs=procedures)


@app.route("/library/procedure/<func>", methods=["GET", "POST"])
def is_empty_book(func):
    values = []
    for item, value in request.form.items():
        if value:
            values.append(value)

    parametr = ','.join(map(str, values))
    @Provider.perform_try
    def procedure(cur):
        cur.execute('CALL %s(%s)' % (func, parametr))

    _, error = procedure()
    flash(error if error else 'Процедура выполнена.')
    return redirect(url_for('procedure'))


@app.route("/library/doc", methods=["GET", "POST"])
def doc():
    docx = ['reminder', 'restoration_book', 'books_udk', 'debtors', 'fdfff']
    return render_template('admin/doc.html', docxs=docx)


@app.route("/library/doc/<docx>", methods=["GET", "POST"])
def docx(docx):
    
    @Provider.perform_try
    def select_try(cur):
        cur.execute('SELECT * FROM %s()' % (docx))
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return columns, value

    value, error = select_try()

    if error:
        flash(error)
        return redirect(url_for("doc"))

    doc = render_docx_template(docx, value[0], value[1])
    return send_file(doc, as_attachment=False)


@app.route("/library/json", methods=["GET", "POST"])
def export_json():
    return render_template("admin/export_json.html", tables=TABLES)


@app.route("/library/json/<table>", methods=["GET", "POST"])
def export_json_table(table):
    
    @Provider.perform_try
    def select(cur):
        cur.execute("SELECT * FROM %s" % (table))
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return value, columns
    
    def convert_date(obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        raise TypeError("Type not serializable")

    value, error = select()
    if error:
        return error
    try:
        dict_data = [dict(zip(value[1], item)) for item in value[0]]
        json_data = json.dumps(dict_data, default=convert_date, ensure_ascii=False, indent=4)
        return json_data
    except Exception as erro:
        return 'Ошибка: %s' % erro


if __name__ == "__main__":
    app.run(debug=True)