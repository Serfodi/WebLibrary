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


"""
- Login / Logout -
"""
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method != "POST":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]
    DB_User(username, password)

    @Provider.perform
    def current_user(cur):
        cur.execute("SELECT * FROM current_user")

    try:
        current_user()
        if user := Users.raw(username):
            session["role"] = user.value
            return redirect(url_for("library"))
            
        return render_template("login.html", error = "Незарегистрированный пользователь: %s" % (user_name))
    except Exception as error:
        print(error)
        return render_template("login.html", error = "Ошибка доступа!")



@app.route("/library")
def library():
    @Provider.perform
    def sql(cur):
        cur.execute("""
        SELECT DISTINCT table_name
          FROM information_schema.table_privileges as it
         WHERE table_schema='public'
	           AND it.privilege_type = 'SELECT'
        """)
        raw = cur.fetchall()
        return [item[0] for item in raw]

    try:
        tables = sql()
        user = session.get('role')
        if user == Users.admin.value or user == Users.librarian.value:
            return render_template("admin/library.html", value=tables, error=None)

        return render_template("library.html", tables=tables, error=None)

    except Exception as error:
        return render_template("library.html", tables=None, error=error)



@app.route("/library/<view>")
def library_view(view):

    @Provider.perform
    def select(cur):
        cur.execute("SELECT * FROM %s" % (view))
        value = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return value, columns

    @Provider.perform
    def privileges(cur):
        cur.execute("""
        SELECT DISTINCT privilege_type
          FROM information_schema.table_privileges as it
         WHERE table_schema='public'
	           AND it.table_name  = '%s'""" % (view))
        value = cur.fetchall()
        return set(desc[0] for desc in value)

    try:
        data, columns = select()
        privileges = privileges()
 
        session['table-name'] = view
        session['columns'] = columns

        if session.get('role') == Users.reader.value :
            return render_template("view.html", view=view, data=data, columns=columns, error=None)
        return render_template("admin/view.html", view=view, data=data, columns=columns, error=None)
    except Exception as error:
        return render_template("view.html", view=None, data=None, columns=None, error=error)



@app.route("/library/<int:row_id>", methods=["DELETE"])
def delete_row(row_id):
    view = session.get('table-name')
    columns = session.get('columns')

    @Provider.perform
    def delete(cur):
        cur.execute("DELETE FROM %s WHERE %s = %s" % (view, columns[0], row_id))

    try:
        delete()
        return "Успешно удалено", 200
    except Exception as error:
        return "Ошибка удаления: %s", (error)



# Добавление
@app.route("/library/<view>/append", methods=["GET", "POST"])
def append_row(view):
    if request.method != "POST":
        return redirect(url_for("library_view", view=view))

    value = []
    columns = session.get('columns')

    @Provider.perform
    def insert(cur):
        parametr = lambda list: ', '.join(map(str, list))
        try:
            cur.execute("INSERT INTO %s (%s) values (%s)" % (view, parametr(columns), parametr(value)))
        except Exception as error:
            print(error)

    try:
        for name in columns:
            value.append(request.form[name])
        insert()

        return redirect(url_for("library_view", view=view))
    except Exception as error:
         return "Ошибка добавления: %s", (error)



@app.route("/library/sql", methods=["GET", "POST"])
def sql():
    if request.method != "POST":
        return render_template("admin/sql.html", data=None, error=None)

    @Provider.perform
    def sql(cur):
        query = request.form["query"]
        cur.execute(query)
        value = cur.fetchall()
        return value

    try:
        data = sql()
        return render_template("admin/sql.html", data=data, error=None) 
    except Exception as error:
        return render_template("admin/sql.html", data=None, error=error)



@app.route("/library/<path:change>", methods=["UPDATE"])
def change_row(change):

    id, column, value = change.split('.')
    view = session.get('table-name')
    columns = session.get('columns')

    print(request.form)

    #newValue = request.form['input1']

    @Provider.perform
    def insert(cur):
        cur.execute("""
        UPDATE %s 
           SET %s = '%s'
         WHERE %s = %s;
        """ % (view, columns[int(column)], value, columns[0], id))

    print("""
        UPDATE %s 
           SET %s = '%s'
         WHERE %s = %s;
        """ % (view, columns[int(column)], value, columns[0], id))

    try:
        insert()
        return "Успешно изменино", 200
    except Exception as error:
        return "Ошибка изменения: %s" % (error)



if __name__ == "__main__":
    app.run(debug=True)