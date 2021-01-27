setup_wearable_table = '''CREATE TABLE wearables (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key text,
        heart_rate real,
        temp real,
        co_level real,
        lat real,
        lon real,
        proximity_sensor real,
        temp_array text,
        image_path text,
        datetime text
)'''

setup_connections = '''CREATE TABLE connections (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key text,
        datetime text
        )'''

setup_users = '''CREATE TABLE users (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        username text,
        password text
)
'''