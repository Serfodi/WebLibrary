
import psycopg2
import enum

DB_HOST = 'postgres'
DB_NAME = 'postgres'
DB_User_Name = 'postgres'
DB_User_Password = 'postgres'

def DB_User(name, password):
    global DB_User_Name
    global DB_User_Password
    DB_User_Name = name
    DB_User_Password = password

class Users(enum.Enum):
    admin = 'admin'
    reader = 'reader'
    postgres = 'postgres'
    
    @classmethod
    def raw(self, value):
        try:
            return self(value)
        except:
            return None

class Provider:
    @staticmethod
    def connection():
        
        connect = psycopg2.connect(
            host = DB_HOST,
            database = DB_NAME,
            user = DB_User_Name,
            password = DB_User_Password
            )
        connect.autocommit = True
        return connect

    @staticmethod
    def perform(block):
        def context():
            connect = Provider.connection()
            cur = connect.cursor()
            value = block(cur)
            cur.close()
            connect.close()
            return value
        return context
    
    @staticmethod
    def perform_try(block):
        def context():
            connect = Provider.connection()
            cur = connect.cursor()
            try:
                value = block(cur)
            except Exception as error:
                print("Error db:",error)
                print(type(error))
                if "no results to fetch" in str(error):
                    return None, None
                return None, 'Error: %s' % (error)
            cur.close()
            connect.close()
            return value, None
        return context
