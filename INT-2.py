import paramiko
import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import codecs

#логин, пароль, порт, ip
class Scan_profile:
    def __init__(self, login, password, port, ip):
        self.login = login
        self.password = password
        self.port = port
        self.ip = ip

#Тип ОС, название ОС, релиз, версии, описание и архитектура
class Info:
    def __init__(self, ostype = None, distr = None, short_version = None, 
                description = None, release = None, full_version = None, 
                codename = None, arch = None):
        self.ostype = ostype
        self.distr = distr
        self.short_version = short_version
        self.description = description
        self.release = release
        self.full_version = full_version
        self.codename = codename
        self.arch = arch

#Креды для подключения к БД
class Database:
    def __init__(self, login = None, password = None, host = None, port = None, database = None):
        self.user = login
        self.password = password
        self.host = host
        self.port = port
        self.database = database

def scan(obj):

    #Подключение по ssh
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:

        ssh.connect(obj.ip, port = obj.port ,username=obj.login, password=obj.password)
        print (f"Вы подключились к узлу {obj.ip}\nНа порт {obj.port}")

        obj_Info = Info()

        #Основная информация
        stdin, stdout, stderr = ssh.exec_command('cat /proc/sys/kernel/{ostype,osrelease,version}')
        ostype, release, full_version = str(stdout.read().decode()[:-1]).split('\n')
        stdin, stdout, stderr = ssh.exec_command('arch')
        arch = str(stdout.read().decode())

        #Дополнительная информация
        stdin, stdout, stderr = ssh.exec_command('lsb_release -a')
        distr, description, short_version, codename =  str(stdout.read().decode()[:-1]).split('\n')
        distr = distr.split("\t")[1]
        description = description.split("\t")[1]
        short_version = short_version.split("\t")[1]
        codename = codename.split("\t")[1]

        ssh.close()

        #Инициализация
        obj_Info.ostype = ostype
        obj_Info.distr = distr
        obj_Info.short_version = short_version
        obj_Info.description = description
        obj_Info.release = release
        obj_Info.full_version = full_version
        obj_Info.codename = codename
        obj_Info.arch = arch

        print (f'Собранная информация:\n' 
               f'Тип ОС: {ostype}\n'
               f'Дистрибутив: {distr}\n'
               f'Короткое версия: {short_version}\n'
               f'Описание: {description}\n'
               f'Релиз: {release}\n'
               f'Полная версия: {full_version}\n'
               f'Кодовое имя: {codename}\n'
               f'Архитектура: {arch}')

        return obj_Info
    
    except (BadHostKeyException, AuthenticationException, SSHException, socket.error) as e:
        print (e)

#Работа с БД
def database_write(obj_scan, ID, obj_db):
    print ("Подключение к базе данных")
    try:
        connection = psycopg2.connect(user=obj_db.user,
                                    password=obj_db.password,
                                    host=obj_db.host,
                                    port=obj_db.port,
                                    database = obj_db.database)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        print("Информация о сервере PostgreSQL")
        print(connection.get_dsn_parameters(), "\n")
        table = 'info'
        cursor.execute('SELECT %s as connected;', ('Успешное подключение к Postgres!',))
        print (f"Создание таблицы {table}")
        create_table_query = f'''CREATE TABLE {table}
                          (ID           INT     PRIMARY KEY     NOT NULL,
                          OSTYPE        TEXT    NOT NULL,
                          DISTR         TEXT    NOT NULL,
                          SHORT_VERSION TEXT    NOT NULL,
                          DESCRIPTION   TEXT    NOT NULL,
                          RELEASE       TEXT    NOT NULL,
                          FULL_VERSION  TEXT    NOT NULL,
                          CODENAME      TEXT    NOT NULL,
                          ARCH          TEXT    NOT NULL); '''
        cursor.execute(create_table_query)

        insert_query = f''' INSERT INTO {table} 
                        (ID, OSTYPE, DISTR, SHORT_VERSION, DESCRIPTION, RELEASE, FULL_VERSION, CODENAME, ARCH) 
                        VALUES ({ID}, '{obj_scan.ostype}', '{obj_scan.distr}', 
                        '{obj_scan.short_version}', '{obj_scan.description}', 
                        '{obj_scan.release}', '{obj_scan.full_version}', 
                        '{obj_scan.codename}', '{obj_scan.arch}')'''
        cursor.execute(insert_query)
        connection.commit()
        print("Запись успешно вставлена")

        connection.commit()

    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Соединение с PostgreSQL закрыто\n")

if __name__ == '__main__':
    file_path = "VM.log"
    
    #sys.stdout = codecs.open(file_path, "a", "utf-8")
    obj_scan = Scan_profile(input("Введите логин: "), input("Введите пароль: "), int(input("Введите пор: ")), input("Введите IP-адрес: "))
    obj_db = Database()
    obj_db.user=input("Введите название имя пользователя: ")
    obj_db.password=input("Введите пароль: ")
    obj_db.host=input("Введите IP-адрес: ")
    obj_db.port=input("Введите порт: ")
    obj_db.database = input("Введите название БД: ")

    buf_obj = scan (obj_scan)
    ID = input("Введите ID записи")
    
    database_write (buf_obj, ID, obj_db)
