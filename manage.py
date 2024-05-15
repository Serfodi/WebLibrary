from flask import Flask, render_template, redirect, flash, url_for, request, session, send_from_directory
from db_connection import Users, DB_User, Provider
from report_gen import create_rent_doc, create_service_doc, create_claim_doc

app = Flask(__name__)
app.secret_key = 'admin'



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



@app.route("/library")
def library():
    tables = ['book', 'periodical', 'libraries', 'udk', 'book_fund', 
              'periodical_fund', 'read_room', 'reader', 'rent_book']
    if session.get('role') == Users.admin.name:
        return render_template("library.html", tables=tables)
    return render_template("library.html", tables=tables[:4])



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

    value = []
    columns = session.get('columns')

    @Provider.perform
    def insert(cur):
        parametr = lambda list: ','.join(map(str, list))
        try:
            cur.execute("INSERT INTO %s (%s) values (%s)" % (table, parametr(columns), parametr(value)))
        except Exception as error:
            print(error)

    try:
        for name in columns:
            value.append(request.form[name])
        insert()

        return redirect(url_for("library_view", table=table))
    except Exception as error:
         return "Ошибка добавления: %s", (error)



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



if __name__ == "__main__":
    app.run(debug=True)