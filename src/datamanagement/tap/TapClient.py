import csv
import io
import requests
import src.datamanagement.database.DbManager as db

BASE_URL = 'https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query='
FIELDS_PATH = 'config/fields.txt'
concat_fields = ''


def load_fields():
    global concat_fields
    with open(FIELDS_PATH, 'r') as file:
        for line in file:
            pair = line.strip().split(':')
            concat_fields += pair[0] + ','
    concat_fields = concat_fields[:-1]


def _form_rows(csv_string):
    tmp = io.StringIO(csv_string)
    reader = csv.reader(tmp)
    next(reader)
    data = []
    for row in reader:
        data.append([None] + row + [None])
    return data


def update():
    db.Database.acquire()

    db_count = db.count()
    assert db_count != -1, 'Database error.'
    db.Database.set_state(1)
    if db_count == 0:
        response = requests.get(BASE_URL + f'select+{concat_fields}+from+ps&format=csv')
        assert response.status_code == 200, f'HTTPError -> response code {response.status_code}'
        rows = _form_rows(response.text)
        db.insert(rows)

    else:
        last_date = db.get_last_date()
        assert last_date is not None
        response = requests.get(
            BASE_URL + f'select+{concat_fields}+from+ps+where+releasedate%3E%3D\'{last_date}\'+or+rowupdate%3E%3D\''
                       f'{last_date}\'&format=csv'
        )
        print(response.text)
        assert response.status_code == 200, f'HTTPError -> response code {response.status_code}'
        rows = _form_rows(response.text)
        names = list(set(row[1] for row in rows))
        if len(names) != 0:
            db.delete(names)
        db.insert(rows)
    db.set_current_date()
    db.Database.set_state(0)

    db.Database.condition().notify_all()
    db.Database.release()

    print("updated")
