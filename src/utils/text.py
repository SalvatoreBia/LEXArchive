def htable_format(headers: list, rows: list, exceeds: bool) -> str:
    head = '''
                <head>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            margin: 20px;
                        }
                        table {
                            width: 100%;
                            border-collapse: collapse;
                            margin-bottom: 20px;
                        }
                        th, td {
                            border: 1px solid #ddd;
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #f2f2f2;
                            color: #333;
                        }
                        tr:nth-child(even) {
                            background-color: #f9f9f9;
                        }
                        tr:hover {
                            background-color: #ddd;
                        }
                        .header h5 {
                            margin: 0;
                        }
                        a {
                            color: #007BFF;
                            text-decoration: none;
                        }
                        a:hover {
                            text-decoration: underline;
                        }
                    </style>
                    
                <title>Table</title>
                </head>
                <body>
            '''
    table = '<table>\n\t<tr>\n'
    for h in headers:
        th = f'\t\t<th id="header"><h5>{h}</h5></th>\n'
        table += th
    table += '\t</tr>\n'

    for row in rows:
        tr = '\t<tr>\n'
        for elem in row:
            th = f'\t\t<th id="record">{elem if elem is not None else ''}</th>\n'
            tr += th
        tr += '\t</tr>\n'
        table += tr
    table += '</table>\n</body>'
    if exceeds:
        table += ('<footer>*Note: this file doesn\'t contain all records. If you want to check all of them, '
                  '<a href="https://exoplanetarchive.ipac.caltech.edu/cgi-bin/TblView/nph-tblView?app=ExoTbls&config'
                  '=PS" target="_blank">visit the official NASA\'s website</a>')
    return head + table


# TODO aggiustare
def planet_spec_format(planet: dict) -> str:
    string = ''
    for key in planet:
        string += f'*{key.replace('*', '\\*').replace('[', '\\[')}* -> _{planet[key] if planet[key] != '' else 'Empty'}_\n'

    return string
