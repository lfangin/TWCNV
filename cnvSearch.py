import csv
from datetime import datetime
import random
#import sqlite3
from flask_mysqldb import MySQL

from flask import Flask, g, render_template, request, make_response
from werkzeug import secure_filename
import os
from flask_bootstrap import Bootstrap

#from model import Session, User, Address
#from datatables import *


app = Flask(__name__)
Bootstrap(app)
mysql = MySQL(app)

#api = Api(app)

#SQLITE_DB_PATH = 'CNVdata.db'
#SQLITE_DB_SCHEMA = 'create_db.sql'
#MEMBER_CSV_PATH = 'members.csv'

app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = set(['txt'])

app.config['MYSQL_USER'] = '****'
app.config['MYSQL_PASSWORD'] = '****'
app.config['MYSQL_DB'] = '****'
app.config['MYSQL_HOST'] = 'localhost'
#mysql.init_app(app)

downLoad=[]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    fr = open('result.csv','r')
    file_contents = fr.read()

    response = make_response(file_contents)
    response.headers["Content-Disposition"] = "attachment; filename=result.csv"
    return response   

def writeFile(downLoad):
    #print(downLoad)
    with open('result.csv','w') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['Gene.symbol','Cytoband','Gene.type','Chromosome','Segment.start','Segment.start','Duplication','Deletion','Male_duplication','Male_deletion','Female_duplication','Female_deletion'])
        for dic in downLoad:
            writer.writerow(dic[key] for key in dic.keys())


@app.route('/reset')
def reset():
    reset_db()
    return render_template('reset.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']
def match(x,recent_uploads):
    db = get_db()
    db.execute(
            "SELECT * FROM myCNVdata WHERE gene_name=%s",
            (x,)
        )

    c_result = db.fetchone()

    if c_result is not None:
        lastStart = c_result[4]
    while c_result is not None:
        if(lastStart!=c_result[5]):
            with db:
               # db.execute('INSERT INTO draw_histories (memberid) VALUES (?)',(c_result[0], ))
                recent_uploads.append({
                    'name': c_result[6],
                    'cytoband':c_result[10],
                    'syn2':c_result[12],
                    'chrom':c_result[13],
                    'start':c_result[14],
                    'end':c_result[15],
                    #'totalCNV':c_result[16],
                    'amp':round(c_result[17]/15829*100,2),
                    'dele':round(c_result[18]/15829*100,2),
                    #'non':c_result[19],
                    'male_amp':round(c_result[20]/7828*100,2),
                    'male_del':round(c_result[21]/7828*100,2),
                    #'male_non':c_result[22],
                    'female_amp':round(c_result[23]/8001*100,2),
                    'female_del':round(c_result[24]/8001*100,2),
                    #'female_non':c_result[25] 
                    })
            lastStart = c_result[5]
        c_result = db.fetchone()


@app.route('/uploadFile', methods=['POST'])
def uploadFile():
    f = request.files['file']
    recent_uploads = []

    if f and allowed_file(f.filename):
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
        with open('./uploads/%s' %f.filename, 'r') as t:
            title = t.readlines()
            title = [x.strip() for x in title]
        for x in title:
            match(x,recent_uploads)
        writeFile(recent_uploads)

    # Render template
    return render_template(
        'upload.html',
        recent_uploads = recent_uploads
    )

@app.route('/uploadText', methods=['POST'])
def uploadText():
    group = request.form.get('gname',' ')
    recent_uploads = []
    match(group,recent_uploads)
    #print(recent_uploads)
    writeFile(recent_uploads)

    # Render template
    return render_template(
        'upload.html',
        recent_uploads = recent_uploads
    )

# SQLite3-related operations
# http://flask.pocoo.org/docs/0.10/patterns/sqlite3/
def get_db():
   # For sqlite
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(SQLITE_DB_PATH)
        # Enable foreign key check
        db.execute("PRAGMA foreign_keys = ON")
    return db
    """
    # For mysql
    cur = mysql.connection.cursor()
    return cur


def reset_db():
    with open(SQLITE_DB_SCHEMA, 'r') as f:
        create_db_sql = f.read()
    db = get_db()
    # Reset database
    # Note that CREATE/DROP table are *immediately* committed
    # even inside a transaction
    with db:
        db.execute("DROP TABLE IF EXISTS draw_histories")
        #db.execute("DROP TABLE IF EXISTS data")
        #db.executescript(create_db_sql)
        db.execute('''CREATE TABLE draw_histories ( memberid INTEGER NOT NULL,time DATETIME DEFAULT (datetime('now', 'localtime')),FOREIGN KEY(memberid) REFERENCES cnvData(id))''')

    # Read members CSV data
    # with open('./database_0607_header.txt') as f:
    #     csv_reader = csv.DictReader(f,delimiter='\t')
    #     data = [
    #         (row['Gene.name'],row['Gene.chromosome'],row['Gene.start'],row['Gene.end'],row['RNA_type'],row['Transcript.chromosome'],row['Transcript.start'], row['Transcript.end'], row['Transcript.ID'], row['Transcript.strand'], row['Amp %'],row['Del %'], row['Male.amp %'], row['Male.del %'], row['Female.amp %'], row['Female.del %'])
    #         for row in csv_reader
    #     ]

    # # Write members into database
    # with db:
    #     db.executemany(
    #         'INSERT INTO data (gene_name, gene_chrom, gene_start, gene_end, RNA_type, \
    #             trans_chrom,trans_start,trans_end,trans_id,trans_strand,amp,             \
    #             _del,male_amp,male_del,female_amp,female_del) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
    #         data
    #     )

@app.route('/history')
def history():
    db = get_db()
    c = db.execute(
        'SELECT m.gene_name, m.chrom, d.time AS "draw_time [timestamp]"'
        'FROM draw_histories AS d, CNVdata as m '
        'WHERE m.id == d.memberid '
        'ORDER BY d.time DESC '
        'LIMIT 10'
    )
    recent_histories = []
    for row in c:
        recent_histories.append({
            'name': row[0],
            'chrom': row[1],
            'draw_time': datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S'),
        })
    return render_template('history.html', recent_histories=recent_histories)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    app.run(debug=True)
