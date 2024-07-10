import requests
import csv
import io
import src.datamanagement.database.DbManager as db

BASE_URL = 'https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query='
FIELDS_PATH = '../../../config/fields.txt'
ps_fields = ''
pscomppars_fields = ''


def load_fields():
    global ps_fields
    global pscomppars_fields
    with open(FIELDS_PATH, 'r') as file:
        for line in file:
            temp = line.strip()
            ps_fields += temp.split(':')[0] + ','
            if not temp.endswith('~'):
                pscomppars_fields += temp.split(':')[0] + ','
        ps_fields = ps_fields[:-1]
        pscomppars_fields = pscomppars_fields[:-1]


def cast(value):
    try:
        if '.' in value:
            return float(value)
        elif value == '':
            return None
        else:
            return int(value)
    except ValueError:
        return value


def form_rows(csv_string):
    f = io.StringIO(csv_string)
    reader = csv.reader(f)
    next(reader)
    matrix = []
    for row in list(reader):
        matrix.append([cast(value) for value in row])
    return matrix


# TODO DA FINIRE
def update():
    query = 'select+count%28*%29+from+pscomppars&format=csv'
    r = requests.get(BASE_URL + query)
    pscomppars_len = r.text.split('\n')[1]
    db_pscomppars_len = db.count('pscomppars')
    db_ps_len = db.count('ps_len')
    if db_pscomppars_len == 0 or pscomppars_len != db_pscomppars_len:
        query = f'select+{pscomppars_fields}+from+pscomppars+top+3&format=csv'
        r = requests.get(BASE_URL + query)
        if r.status_code != 200:
            return

        for row in form_rows(r.text):
            db.insert('pscomppars', len(row)+2, [None]+row+[None])

    if db_ps_len == 0:
        query = f'select+{ps_fields}+from+ps+top+3&format=csv'
        r = requests.get(BASE_URL + query)
        if r.status_code != 200:
            return

        for row in form_rows(r.text):
            db.insert('ps', len(row)+1, [None]+row)
    else:
        date = db.get_last_date()


if __name__ == '__main__':
    load_fields()
    update()
